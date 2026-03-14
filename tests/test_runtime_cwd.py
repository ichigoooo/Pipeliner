from __future__ import annotations

import sys
from pathlib import Path

from pipeliner.executor import ClaudeExecutorDispatcher, ClaudeValidatorDispatcher
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)


def _register_workflow(client, workflow_fixture) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client, workflow_id: str, version: str) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": workflow_id,
            "version": version,
            "inputs": {"topic": "cwd test"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def _dispatch_executor(client, settings, run_id: str) -> None:
    script = Path("tests/fixtures/mock_claude_executor.py").resolve()
    command = f"{sys.executable} {script} {{task_file}}"
    with client.app.state.db.session() as session:
        dispatcher = ClaudeExecutorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = dispatcher.dispatch(
            run_id=run_id,
            node_id="draft_article",
            command_template=command,
        )
        assert result["status"] == "completed"


def test_executor_dispatch_uses_project_root(
    client,
    workflow_fixture,
    settings,
    monkeypatch,
    tmp_path,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    marker = tmp_path / "executor_cwd.txt"
    monkeypatch.setenv("PIPELINER_TEST_CWD_FILE", str(marker))

    _dispatch_executor(client, settings, run["run_id"])

    expected = settings.projects_root / "mvp-review-loop"
    assert marker.read_text(encoding="utf-8") == str(expected)


def test_validator_dispatch_uses_project_root(
    client,
    workflow_fixture,
    settings,
    monkeypatch,
    tmp_path,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    _dispatch_executor(client, settings, run["run_id"])

    marker = tmp_path / "validator_cwd.txt"
    monkeypatch.setenv("PIPELINER_TEST_CWD_FILE", str(marker))
    script = Path("tests/fixtures/mock_claude_validator.py").resolve()
    command = f"{sys.executable} {script} pass"

    with client.app.state.db.session() as session:
        dispatcher = ClaudeValidatorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = dispatcher.dispatch(
            run_id=run["run_id"],
            node_id="draft_article",
            validator_id="content-review",
            command_template=command,
        )
        assert result["status"] == "pass"

    expected = settings.projects_root / "mvp-review-loop"
    assert marker.read_text(encoding="utf-8") == str(expected)
