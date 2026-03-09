from __future__ import annotations

import sys
from pathlib import Path

from pipeliner.executor import ClaudeExecutorDispatcher
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
            "inputs": {"topic": "claude executor test"},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_dispatch_executor_success(client, workflow_fixture, settings) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
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
            run_id=run["run_id"],
            node_id="draft_article",
            command_template=command,
        )
        assert result["status"] == "completed"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    node = next(item for item in detail.json()["nodes"] if item["node_id"] == "draft_article")
    assert node["status"] == "waiting_validator"
    assert detail.json()["artifacts"][0]["artifact_id"] == "article_draft"

    callbacks = client.get(f"/api/runs/{run['run_id']}/callbacks")
    assert callbacks.status_code == 200
    assert len(callbacks.json()["events"]) == 1
    assert callbacks.json()["events"][0]["actor_role"] == "executor"


def test_dispatch_executor_failure_marks_attention(client, workflow_fixture, settings) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")

    with client.app.state.db.session() as session:
        dispatcher = ClaudeExecutorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = dispatcher.dispatch(
            run_id=run["run_id"],
            node_id="draft_article",
            command_template="definitely_not_existing_command",
        )
        assert result["status"] == "failed"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "needs_attention"
    node = next(item for item in detail.json()["nodes"] if item["node_id"] == "draft_article")
    assert node["status"] == "failed"


def test_dispatch_executor_default_command_reads_prompt_stdin(
    client,
    workflow_fixture,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    script = Path("tests/fixtures/mock_claude_executor_stdin.py").resolve()
    settings.claude_executor_cmd = f"{sys.executable} {script}"

    with client.app.state.db.session() as session:
        dispatcher = ClaudeExecutorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = dispatcher.dispatch(run_id=run["run_id"], node_id="draft_article")
        assert result["status"] == "completed"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    node = next(item for item in detail.json()["nodes"] if item["node_id"] == "draft_article")
    assert node["status"] == "waiting_validator"


def test_dispatch_executor_missing_artifact_marks_attention(
    client,
    workflow_fixture,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    script = Path("tests/fixtures/mock_claude_executor_no_output.py").resolve()
    command = f"{sys.executable} {script}"

    with client.app.state.db.session() as session:
        dispatcher = ClaudeExecutorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            settings,
        )
        result = dispatcher.dispatch(
            run_id=run["run_id"],
            node_id="draft_article",
            command_template=command,
        )
        assert result["status"] == "failed"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "needs_attention"
    node = next(item for item in detail.json()["nodes"] if item["node_id"] == "draft_article")
    assert node["status"] == "failed"
