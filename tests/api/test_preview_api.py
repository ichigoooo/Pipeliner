from __future__ import annotations

import subprocess

from fastapi.testclient import TestClient


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client: TestClient, workflow_id: str, version: str) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": workflow_id,
            "version": version,
            "inputs": {"topic": "preview api"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_artifact_and_log_preview(client: TestClient, workflow_fixture, settings, workspace_manager, monkeypatch) -> None:
    _register_workflow(client, workflow_fixture)
    run_info = _start_run(client, "mvp-review-loop", "0.1.0")

    artifact_rel = (
        f"{run_info['workspace_root']}/artifacts/article_draft@v1/payload/article.md"
    )
    artifact_path = settings.data_dir / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("preview content", encoding="utf-8")
    digest, size = workspace_manager.compute_digest(artifact_path)

    manifest = {
        "schema_version": "pipeliner.artifact/v1alpha1",
        "artifact_id": "article_draft",
        "version": "v1",
        "kind": "file",
        "produced_by": {
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 1,
            "role": "executor",
        },
        "storage": {"backend": "local_fs", "uri": artifact_rel},
        "integrity": {"digest": digest, "size_bytes": size},
        "created_at": "2026-03-11T00:00:00+00:00",
    }
    publish_response = client.post("/api/artifacts", json=manifest)
    assert publish_response.status_code == 200

    preview_response = client.get(
        f"/api/runs/{run_info['run_id']}/artifacts/article_draft/versions/v1/preview"
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["preview"]["kind"] == "text"
    assert "preview content" in preview_payload["preview"]["content"]

    opened_commands: list[list[str]] = []

    def _mock_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        opened_commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("pipeliner.services.preview_service.subprocess.run", _mock_run)

    open_response = client.post(
        f"/api/runs/{run_info['run_id']}/artifacts/article_draft/versions/v1/open-folder"
    )
    assert open_response.status_code == 200
    open_payload = open_response.json()
    assert open_payload["artifact_id"] == "article_draft"
    assert open_payload["version"] == "v1"
    assert open_payload["target_path"].endswith("/article.md")
    assert open_payload["opened_path"].endswith("/artifacts/article_draft@v1/payload")
    assert opened_commands
    assert opened_commands[0][-1].endswith("/artifacts/article_draft@v1/payload")

    log_rel = "nodes/draft_article/rounds/1/executor/executor_stdout.log"
    log_path = settings.data_dir / run_info["workspace_root"] / log_rel
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("log preview", encoding="utf-8")

    log_response = client.get(
        f"/api/runs/{run_info['run_id']}/logs/preview",
        params={"path": log_rel},
    )
    assert log_response.status_code == 200
    log_payload = log_response.json()
    assert log_payload["preview"]["kind"] == "text"
    assert "log preview" in log_payload["preview"]["content"]
