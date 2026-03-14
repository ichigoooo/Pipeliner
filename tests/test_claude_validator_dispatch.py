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
            "inputs": {"topic": "claude validator test"},
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


def test_dispatch_validator_pass_activates_downstream(client, workflow_fixture, settings) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    _dispatch_executor(client, settings, run["run_id"])

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
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    draft_rounds = [
        item for item in detail.json()["nodes"] if item["node_id"] == "draft_article"
    ]
    assert draft_rounds[-1]["status"] == "passed"
    final_review = next(
        item for item in detail.json()["nodes"] if item["node_id"] == "final_review"
    )
    assert final_review["status"] == "waiting_executor"


def test_dispatch_validator_revise_creates_next_round(client, workflow_fixture, settings) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    _dispatch_executor(client, settings, run["run_id"])

    script = Path("tests/fixtures/mock_claude_validator.py").resolve()
    command = f"{sys.executable} {script} revise"
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
        assert result["status"] == "revise"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    draft_rounds = [item for item in detail.json()["nodes"] if item["node_id"] == "draft_article"]
    assert len(draft_rounds) == 2
    assert draft_rounds[0]["status"] == "revise"
    assert draft_rounds[1]["status"] == "waiting_executor"
    assert draft_rounds[1]["round_no"] == 2


def test_dispatch_validator_missing_result_marks_attention(
    client,
    workflow_fixture,
    settings,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client, "mvp-review-loop", "0.1.0")
    _dispatch_executor(client, settings, run["run_id"])

    script = Path("tests/fixtures/mock_claude_validator.py").resolve()
    command = f"{sys.executable} {script} none"
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
        assert result["status"] == "failed"
        assert result["runtime"]["duplicate"] is False

    detail = client.get(f"/api/runs/{run['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "needs_attention"
    draft_round = next(
        item for item in detail.json()["nodes"] if item["node_id"] == "draft_article"
    )
    assert draft_round["status"] == "failed"
