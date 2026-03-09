from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pipeliner.persistence.repositories import WorkflowRepository
from pipeliner.protocols.callback import NodeCallbackPayload
from pipeliner.services.workflow_service import WorkflowLintError, WorkflowService


def test_validator_revise_requires_non_empty_must_fix() -> None:
    with pytest.raises(ValueError):
        NodeCallbackPayload.model_validate(
            {
                "schema_version": "pipeliner.callback/v1alpha1",
                "event_id": "evt_1",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "run_1",
                "node_id": "draft_article",
                "round_no": 1,
                "actor": {"role": "validator", "validator_id": "reviewer"},
                "execution": {"status": "completed"},
                "verdict": {"status": "revise", "target_artifacts": [], "summary": "needs fixes"},
                "rework_brief": {"must_fix": []},
            }
        )


def test_workflow_cycle_detection(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["nodes"][0]["depends_on"] = ["final_review"]
        workflow_fixture["nodes"][0]["inputs"].append(
            {
                "name": "loop_input",
                "from": {
                    "kind": "node_output",
                    "node_id": "final_review",
                    "output": "approved_article",
                },
                "shape": "file",
                "required": True,
                "summary": "illegal loop",
            }
        )
        with pytest.raises(WorkflowLintError):
            service.validate_spec(workflow_fixture)


def test_reject_unknown_workflow_schema_version(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["schema_version"] = "pipeliner.workflow/v2alpha1"
        with pytest.raises(ValueError):
            service.validate_spec(workflow_fixture)
