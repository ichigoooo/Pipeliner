from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import time

from fastapi.testclient import TestClient

from pipeliner.db import Database
from pipeliner.persistence.repositories import RunRepository
from pipeliner.protocols.artifact import ArtifactManifest, ArtifactStorage, ProducedBy
from pipeliner.services.run_drive_coordinator import RunDriveCoordinator
from pipeliner.storage.local_fs import WorkspaceManager
from pipeliner.types import ActorRole, ArtifactKind, StorageBackend


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client: TestClient, workflow_id: str, version: str) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": workflow_id,
            "version": version,
            "inputs": {"topic": "run drive api"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def _wait_for_driver(client: TestClient, run_id: str, timeout: float = 5.0) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        response = client.get(f"/api/runs/{run_id}/debug/overview")
        assert response.status_code == 200
        payload = response.json()
        if payload["driver"]["status"] != "running":
            return payload
        time.sleep(0.05)
    raise AssertionError("driver did not finish in time")


def test_run_drive_api_completes_run(client: TestClient, workflow_fixture: dict) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")

    executor_script = Path("tests/fixtures/mock_claude_executor.py").resolve()
    validator_script = Path("tests/fixtures/mock_pipeline_validator_sequence.py").resolve()
    executor_command = f"{sys.executable} {executor_script} {{task_file}}"
    validator_command = f"{sys.executable} {validator_script}"

    response = client.post(
        f"/api/runs/{run['run_id']}/drive",
        json={
            "max_steps": 10,
            "executor_command_template": executor_command,
            "validator_command_template": validator_command,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["steps"]


def test_run_creation_auto_drives_and_exposes_live_overview(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    executor_script = Path("tests/fixtures/mock_claude_executor_slow.py").resolve()
    validator_script = Path("tests/fixtures/mock_pipeline_validator_sequence.py").resolve()
    settings.claude_executor_cmd = f"{sys.executable} {executor_script} {{task_file}}"
    settings.claude_validator_cmd = f"{sys.executable} {validator_script}"

    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "auto drive"},
            "auto_drive": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["driver"]["status"] == "running"

    overview_response = client.get(f"/api/runs/{payload['run_id']}/debug/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["driver"]["status"] == "running"
    assert overview["current_focus"]["node_id"] == "draft_article"
    assert overview["activity"]
    assert any(item["kind"] == "node_round_created" for item in overview["activity"])

    final_overview = _wait_for_driver(client, payload["run_id"])
    assert final_overview["driver"]["status"] == "completed"


def test_manual_drive_conflicts_with_active_auto_driver(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    executor_script = Path("tests/fixtures/mock_claude_executor_slow.py").resolve()
    validator_script = Path("tests/fixtures/mock_pipeline_validator_sequence.py").resolve()
    settings.claude_executor_cmd = f"{sys.executable} {executor_script} {{task_file}}"
    settings.claude_validator_cmd = f"{sys.executable} {validator_script}"

    run_response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "auto drive conflict"},
            "auto_drive": True,
        },
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    conflict = client.post(f"/api/runs/{run_id}/drive", json={"max_steps": 10})
    assert conflict.status_code == 409
    assert "已有 driver 在运行" in conflict.json()["detail"]

    _wait_for_driver(client, run_id)


def test_driver_failure_is_persisted_to_run_status(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    coordinator = RunDriveCoordinator(Database(settings), settings)
    coordinator._begin_run(run["run_id"], mode="auto", max_steps=10)
    coordinator._finish_failure(run["run_id"], "simulated crash")

    overview = client.get(f"/api/runs/{run['run_id']}/debug/overview")
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["status"] == "needs_attention"
    assert payload["stop_reason"] == "driver failed: simulated crash"
    assert payload["latest_nodes"][0]["status"] == "failed"


def test_debug_overview_reconciles_archived_callbacks(
    client: TestClient,
    workflow_fixture: dict,
    workspace_manager: WorkspaceManager,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    run_id = run["run_id"]
    workspace = workspace_manager.get_workspace("mvp-review-loop", run_id)

    payload_path = workspace.artifacts_dir / "article_draft@v1" / "payload" / "article_draft.md"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text("# draft\n", encoding="utf-8")
    digest, size = workspace_manager.compute_digest(payload_path)
    manifest = ArtifactManifest(
        artifact_id="article_draft",
        version="v1",
        kind=ArtifactKind.FILE,
        produced_by=ProducedBy(
            run_id=run_id,
            node_id="draft_article",
            round_no=1,
            role=ActorRole.EXECUTOR,
        ),
        storage=ArtifactStorage(
            backend=StorageBackend.LOCAL_FS,
            uri=f"{workspace.relative_root}/artifacts/article_draft@v1/payload/article_draft.md",
        ),
        integrity={"digest": digest, "size_bytes": size},
        created_at=datetime.now(timezone.utc),
    )
    manifest_path = workspace_manager.artifact_manifest_path(workspace, "article_draft", "v1")
    workspace_manager.write_json(manifest_path, manifest.model_dump(mode="json"))

    workspace_manager.write_callback_archive(
        workspace,
        "evt_exec_reconcile",
        {
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_exec_reconcile",
            "sent_at": "2026-03-16T10:03:40Z",
            "run_id": run_id,
            "node_id": "draft_article",
            "round_no": 1,
            "actor": {"role": "executor", "validator_id": None},
            "execution": {"status": "completed", "message": None},
            "submission": {"artifacts": [{"artifact_id": "article_draft", "version": "v1"}]},
            "verdict": None,
            "rework_brief": None,
        },
    )
    workspace_manager.write_callback_archive(
        workspace,
        "evt_val_reconcile",
        {
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_val_reconcile",
            "sent_at": "2026-03-16T10:05:07Z",
            "run_id": run_id,
            "node_id": "draft_article",
            "round_no": 1,
            "actor": {"role": "validator", "validator_id": "content-review"},
            "execution": {"status": "completed", "message": None},
            "submission": None,
            "verdict": {
                "status": "pass",
                "target_artifacts": [],
                "summary": "looks good",
            },
            "rework_brief": None,
        },
    )

    overview_response = client.get(f"/api/runs/{run_id}/debug/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    latest_nodes = {item["node_id"]: item for item in overview["latest_nodes"]}
    assert latest_nodes["draft_article"]["status"] == "passed"
    assert latest_nodes["final_review"]["status"] == "waiting_executor"

    callbacks_response = client.get(f"/api/runs/{run_id}/callbacks")
    assert callbacks_response.status_code == 200
    assert len(callbacks_response.json()["events"]) == 2

    artifacts_response = client.get(f"/api/runs/{run_id}/artifacts")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["artifacts"][0]["artifact_id"] == "article_draft"


def test_debug_overview_reconciles_stale_executor_call(
    client: TestClient,
    workflow_fixture: dict,
    workspace_manager: WorkspaceManager,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    run_id = run["run_id"]
    workspace = workspace_manager.get_workspace("mvp-review-loop", run_id)

    workspace_manager.write_json(
        workspace.nodes_dir / "draft_article" / "rounds" / "1" / "executor" / "claude_call.json",
        {"call_id": "call_stale_1"},
    )
    call_dir = settings.data_dir / "claude_calls"
    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "call_stale_1.log").write_text("", encoding="utf-8")
    (call_dir / "call_stale_1.json").write_text(
        json.dumps(
            {
                "call_id": "call_stale_1",
                "role": "executor",
                "status": "running",
                "started_at": "2026-03-16T10:00:00+00:00",
                "ended_at": None,
                "exit_code": None,
                "error_message": None,
                "bytes_written": 0,
                "truncated": False,
                "limit_bytes": 2000000,
                "output_path": "claude_calls/call_stale_1.log",
                "command": "claude -p",
                "context": {"run_id": run_id, "node_id": "draft_article", "round_no": 1},
                "pid": 999999,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with Database(settings).session() as session:
        node_run = RunRepository(session).get_node_run(run_id, "draft_article", 1)
        assert node_run is not None
        node_run.updated_at = datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)

    overview_response = client.get(f"/api/runs/{run_id}/debug/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["status"] == "needs_attention"
    assert overview["latest_nodes"][0]["status"] == "failed"
    assert "claude process exited unexpectedly" in overview["latest_nodes"][0]["stop_reason"]


def test_debug_overview_keeps_true_wait_timeout_as_timed_out(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    run_id = run["run_id"]

    with Database(settings).session() as session:
        node_run = RunRepository(session).get_node_run(run_id, "draft_article", 1)
        assert node_run is not None
        node_run.updated_at = datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)

    overview_response = client.get(f"/api/runs/{run_id}/debug/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["status"] == "needs_attention"
    assert overview["latest_nodes"][0]["status"] == "timed_out"
    assert overview["latest_nodes"][0]["stop_reason"] == "timeout guard exceeded"


def test_dispatch_executor_prompt_includes_executor_skill(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    executor_script = Path("tests/fixtures/mock_claude_executor_no_output.py").resolve()
    command = f"{sys.executable} {executor_script}"

    response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/executor/dispatch",
        json={"command_template": command},
    )
    assert response.status_code == 200

    prompt_path = (
        settings.data_dir
        / "runs"
        / "mvp-review-loop"
        / run["run_id"]
        / "nodes"
        / "draft_article"
        / "rounds"
        / "1"
        / "executor"
        / "claude_prompt.md"
    )
    prompt = prompt_path.read_text(encoding="utf-8")
    assert "executor_skill: `draft-wechat-article`" in prompt
    assert ".claude/skills/draft-wechat-article/SKILL.md" in prompt
    assert "skill_reference:" in prompt

    mirror_dir = (
        settings.projects_root
        / "mvp-review-loop"
        / ".pipeliner"
        / "logs"
        / "runs"
        / run["run_id"]
        / "draft_article"
        / "rounds"
        / "1"
        / "executor"
    )
    assert (mirror_dir / "claude_call.json").exists()
    assert (mirror_dir / "claude_call.log").exists()
    assert (mirror_dir / "stdout.log").exists()
    assert (mirror_dir / "stderr.log").exists()
    events_path = mirror_dir / "execution_events.jsonl"
    assert events_path.exists()
    events_text = events_path.read_text(encoding="utf-8")
    assert '"event": "dispatch_prepared"' in events_text
    assert '"event": "process_started"' in events_text
    assert '"event": "process_exited"' in events_text


def test_executor_first_byte_timeout_is_classified_as_failure(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    workflow_fixture["defaults"]["runtime_guards"]["first_byte_timeout"] = "1s"
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    executor_script = Path("tests/fixtures/mock_claude_executor_hang.py").resolve()
    command = f"{sys.executable} {executor_script} {{task_file}}"

    response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/executor/dispatch",
        json={"command_template": command},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"

    overview_response = client.get(f"/api/runs/{run['run_id']}/debug/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["status"] == "needs_attention"
    assert overview["latest_nodes"][0]["status"] == "failed"
    assert overview["latest_nodes"][0]["stop_reason"] == "executor first byte timeout"
