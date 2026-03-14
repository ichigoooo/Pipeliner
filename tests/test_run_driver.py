from __future__ import annotations

import sys
from pathlib import Path

from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.services.run_driver import RunDriver


def _register_workflow(client, workflow_fixture) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client, workflow_id: str, version: str) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": workflow_id,
            "version": version,
            "inputs": {"topic": "run driver test"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_run_driver_completes_workflow(client, workflow_fixture, settings) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")

    executor_script = Path("tests/fixtures/mock_claude_executor.py").resolve()
    validator_script = Path("tests/fixtures/mock_pipeline_validator_sequence.py").resolve()
    executor_command = f"{sys.executable} {executor_script} {{task_file}}"
    validator_command = f"{sys.executable} {validator_script}"

    with client.app.state.db.session() as session:
        driver = RunDriver(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = driver.drive(
            run_id=run["run_id"],
            executor_command_template=executor_command,
            validator_command_template=validator_command,
            max_steps=10,
        )

    assert result["status"] == "completed"
    assert len(result["steps"]) == 6

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "completed"
    assert any(item["artifact_id"] == "approved_article" for item in detail.json()["artifacts"])
