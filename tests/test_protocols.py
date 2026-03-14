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


def test_reject_invalid_skill_name(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["nodes"][0]["executor"]["skill"] = "Bad_Skill"
        with pytest.raises(ValueError):
            service.validate_spec(workflow_fixture)


def test_reject_reserved_skill_name(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["nodes"][0]["executor"]["skill"] = "workflow-authoring"
        with pytest.raises(ValueError):
            service.validate_spec(workflow_fixture)


def test_reject_duplicate_skill_names(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        duplicate = workflow_fixture["nodes"][0]["executor"]["skill"]
        workflow_fixture["nodes"][1]["validators"][0]["skill"] = duplicate
        with pytest.raises(ValueError):
            service.validate_spec(workflow_fixture)


def test_workflow_input_form_metadata_supports_defaults_and_validation(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["inputs"] = [
            {
                "name": "topic",
                "shape": "string",
                "required": True,
                "summary": "Requested topic",
                "form": {
                    "type": "enum",
                    "options": ["science", "history"],
                    "default": "science",
                },
            },
            {
                "name": "retry_count",
                "shape": "number",
                "required": False,
                "summary": "Optional retry count",
                "form": {
                    "type": "number",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                },
            },
        ]
        workflow_fixture["nodes"][0]["inputs"].append(
            {
                "name": "retry_count",
                "from": {"kind": "workflow_input", "name": "retry_count"},
                "shape": "number",
                "required": False,
                "summary": "Retry count",
            }
        )

        spec, _warnings = service.validate_spec(workflow_fixture)
        normalized = service.validate_run_inputs(spec, {"topic": "history"})

        assert normalized == {"topic": "history", "retry_count": 2}
        descriptor = spec.inputs[0].normalized_descriptor()
        assert descriptor.input_type == "enum"
        assert descriptor.source == "explicit"


def test_workflow_input_form_metadata_rejects_invalid_enum_and_default(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_fixture["inputs"][0]["form"] = {
            "type": "enum",
            "options": ["science"],
            "default": "history",
        }
        with pytest.raises(ValueError):
            service.validate_spec(workflow_fixture)


def test_workflow_input_descriptor_derives_from_legacy_shape(client, workflow_fixture) -> None:
    with client.app.state.db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        spec, _warnings = service.validate_spec(workflow_fixture)
        descriptor = spec.inputs[0].normalized_descriptor()

        assert descriptor.input_type == "string"
        assert descriptor.source == "derived"
