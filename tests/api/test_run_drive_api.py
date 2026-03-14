from __future__ import annotations

import sys
from pathlib import Path
import time

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
