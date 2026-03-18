from __future__ import annotations

from fastapi.testclient import TestClient

from pipeliner.persistence.repositories import RunRepository


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client: TestClient) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "studio api test"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_workflow_and_run_studio_endpoints(client: TestClient, workflow_fixture: dict) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)

    workflows_response = client.get("/api/workflows")
    assert workflows_response.status_code == 200
    assert workflows_response.json()["workflows"][0]["workflow_id"] == "mvp-review-loop"

    versions_response = client.get("/api/workflows/mvp-review-loop/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()["versions"][0]["version"] == "0.1.0"

    workflow_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0")
    assert workflow_response.status_code == 200
    assert workflow_response.json()["graph"]["nodes"]
    assert workflow_response.json()["workflow_view"]["cards"]
    assert workflow_response.json()["workflow_view"]["input_descriptors"][0]["type"] == "string"

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["runs"][0]["run_id"] == run["run_id"]

    overview_response = client.get(f"/api/runs/{run['run_id']}/debug/overview")
    assert overview_response.status_code == 200
    assert overview_response.json()["timeline"][0]["node_id"] == "draft_article"
    assert overview_response.json()["driver"]["status"] == "idle"
    assert overview_response.json()["current_focus"]["node_id"] == "draft_article"
    assert overview_response.json()["activity"]

    round_response = client.get(
        f"/api/runs/{run['run_id']}/debug/nodes/draft_article/rounds/1"
    )
    assert round_response.status_code == 200
    assert round_response.json()["context"]["node"]["node_id"] == "draft_article"
    assert round_response.json()["log_refs"]


def test_run_creation_validates_typed_workflow_inputs(client: TestClient, workflow_fixture: dict) -> None:
    workflow_fixture["inputs"][0]["form"] = {
        "type": "enum",
        "options": ["science", "history"],
    }
    _register_workflow(client, workflow_fixture)

    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "finance"},
            "auto_drive": False,
        },
    )

    assert response.status_code == 400
    assert "必须是以下值之一" in response.json()["detail"]


def test_run_creation_accepts_manual_file_path_inputs(client: TestClient, workflow_fixture: dict) -> None:
    workflow_fixture["inputs"][0] = {
        "name": "source_file",
        "shape": "file",
        "required": True,
        "summary": "Source file path",
        "form": {
            "type": "file",
            "min_length": 1,
        },
    }
    workflow_fixture["nodes"][0]["inputs"][0] = {
        "name": "source_file",
        "from": {"kind": "workflow_input", "name": "source_file"},
        "shape": "file",
        "required": True,
        "summary": "Source file path",
    }
    _register_workflow(client, workflow_fixture)

    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"source_file": "/tmp/source.md"},
            "auto_drive": False,
        },
    )

    assert response.status_code == 200


def test_attention_retry_and_settings_snapshot(
    client: TestClient,
    workflow_fixture: dict,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)

    dispatch_response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/executor/dispatch",
        json={"command_template": "definitely_not_existing_command"},
    )
    assert dispatch_response.status_code == 200

    attention_response = client.get("/api/runs/attention")
    assert attention_response.status_code == 200
    assert attention_response.json()["runs"][0]["run_id"] == run["run_id"]
    assert "retry_node" in attention_response.json()["runs"][0]["actions"]

    retry_response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/retry",
        json={"rework_brief": {"summary": "retry from studio"}},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["round_no"] == 2
    assert retry_response.json()["waiting_for_role"] == "executor"

    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200
    payload = settings_response.json()["settings"]
    assert payload["executor_command"]["source"] in {"default", "env"}
    assert payload["storage"]["backend"]["value"] == "local_fs"
    assert payload["runtime_guards"]["default_timeout"]["value"] == "2h"
    assert isinstance(payload["skills"], list)
    assert "claude_diagnostics" in payload
    diagnostics = payload["claude_diagnostics"]
    assert "base_url" in diagnostics
    assert "api_host" in diagnostics
    assert "proxy" in diagnostics
    assert isinstance(diagnostics["proxy"]["missing"], bool)


def test_delete_non_running_run_removes_workspace_and_list_entries(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)
    workspace_path = settings.data_dir / run["workspace_root"]
    marker = workspace_path / "nodes" / "marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("delete me", encoding="utf-8")

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        run_model = run_repo.get_run(run["run_id"])
        node_run = run_repo.get_latest_node_run(run["run_id"], "draft_article")
        assert run_model is not None
        assert node_run is not None
        run_model.status = "needs_attention"
        run_model.stop_reason = "blocked"
        node_run.status = "blocked"

    delete_response = client.delete(f"/api/runs/{run['run_id']}")
    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload["run_id"] == run["run_id"]
    assert delete_payload["deleted"] is True
    assert not workspace_path.exists()

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    assert all(item["run_id"] != run["run_id"] for item in runs_response.json()["runs"])

    attention_response = client.get("/api/runs/attention")
    assert attention_response.status_code == 200
    assert all(item["run_id"] != run["run_id"] for item in attention_response.json()["runs"])

    detail_response = client.get(f"/api/runs/{run['run_id']}")
    assert detail_response.status_code == 404


def test_delete_running_run_is_rejected(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)
    workspace_path = settings.data_dir / run["workspace_root"]

    response = client.delete(f"/api/runs/{run['run_id']}")
    assert response.status_code == 400
    assert "不允许删除" in response.json()["detail"]
    assert workspace_path.exists()


def test_delete_run_succeeds_even_when_workspace_already_missing(
    client: TestClient,
    workflow_fixture: dict,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)
    workspace_path = settings.data_dir / run["workspace_root"]
    if workspace_path.exists():
        for child in sorted(workspace_path.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        workspace_path.rmdir()

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        run_model = run_repo.get_run(run["run_id"])
        assert run_model is not None
        run_model.status = "stopped"
        run_model.stop_reason = "manual_stop"

    response = client.delete(f"/api/runs/{run['run_id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_bulk_delete_runs_removes_multiple_non_running_runs(
    client: TestClient,
    workflow_fixture: dict,
) -> None:
    _register_workflow(client, workflow_fixture)
    run_a = _start_run(client)
    run_b = _start_run(client)

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        for run_id in (run_a["run_id"], run_b["run_id"]):
            run_model = run_repo.get_run(run_id)
            assert run_model is not None
            run_model.status = "completed"

    response = client.post(
        "/api/runs/bulk-delete",
        json={"run_ids": [run_a["run_id"], run_b["run_id"]]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted"] is True
    assert payload["deleted_count"] == 2
    assert payload["run_ids"] == [run_a["run_id"], run_b["run_id"]]

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    remaining_ids = {item["run_id"] for item in runs_response.json()["runs"]}
    assert run_a["run_id"] not in remaining_ids
    assert run_b["run_id"] not in remaining_ids
