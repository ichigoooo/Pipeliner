from __future__ import annotations

import subprocess
import time

from fastapi.testclient import TestClient


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _wait_for_batch(client: TestClient, batch_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/batch-runs/{batch_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["batch"]["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"batch {batch_id} did not reach a terminal state")


def test_batch_run_template_and_detail(client: TestClient, workflow_fixture: dict, monkeypatch) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    assert template_response.status_code == 200
    assert template_response.text.strip() == "topic"

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={"file": ("inputs.csv", "topic\nalpha\n \n", "text/csv")},
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["workflow_id"] == "mvp-review-loop"
    assert create_payload["version"] == "0.1.0"
    assert create_payload["total_count"] == 2
    assert create_payload["failed_count"] == 1

    detail_payload = _wait_for_batch(client, create_payload["batch_id"])
    assert detail_payload["batch"]["status"] == "completed"
    assert detail_payload["batch"]["success_count"] == 1
    assert detail_payload["batch"]["failed_count"] == 1
    assert len(detail_payload["items"]) == 2
    assert detail_payload["items"][0]["status"] == "completed"
    assert detail_payload["items"][0]["run_id"] is not None
    assert detail_payload["items"][1]["status"] == "failed"
    assert "缺少必填 workflow inputs" in detail_payload["items"][1]["error_message"]
    assert "topic" in detail_payload["items"][1]["error_message"]


def test_open_run_workspace_endpoint(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    run_response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "open workspace"},
            "auto_drive": False,
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()

    opened_commands: list[list[str]] = []

    def _mock_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        opened_commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("pipeliner.services.preview_service.subprocess.run", _mock_run)

    open_response = client.post(f"/api/runs/{run_payload['run_id']}/open-folder")
    assert open_response.status_code == 200
    open_payload = open_response.json()
    assert open_payload["run_id"] == run_payload["run_id"]
    assert open_payload["opened_path"].endswith(run_payload["run_id"])
    assert opened_commands
    assert opened_commands[0][-1].endswith(run_payload["run_id"])
