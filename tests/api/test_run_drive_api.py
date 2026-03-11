from __future__ import annotations

import sys
from pathlib import Path

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
            "inputs": {"topic": "run drive api"},
        },
    )
    assert response.status_code == 200
    return response.json()


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
