from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from pipeliner.persistence.models import AuthoringGenerationLogModel


def _valid_authoring_spec(version: str = "v1.0.0") -> dict:
    return {
        "schema_version": "pipeliner.workflow/v1alpha1",
        "metadata": {
            "workflow_id": "authoring_generate",
            "version": version,
            "title": "Authoring Generate",
            "purpose": "Verify authoring generate flow",
            "tags": ["studio"],
        },
        "inputs": [],
        "outputs": [],
        "nodes": [],
        "defaults": {"runtime_guards": {"timeout": "30m", "max_rework_rounds": 3}},
        "extensions": {},
    }


def test_authoring_generate_creates_revision(client: TestClient, settings) -> None:
    script = Path("tests/fixtures/mock_claude_authoring.py").resolve()
    settings.claude_authoring_cmd = f"{sys.executable} {script} {{task_file}}"

    response = client.post(
        "/api/authoring/sessions",
        json={"title": "Authoring Generate", "intent_brief": "Generate a workflow draft"},
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    generate_response = client.post(
        f"/api/authoring/sessions/{session_id}/generate",
        json={
            "instruction": "Add a draft spec",
            "spec": _valid_authoring_spec(),
        },
    )
    assert generate_response.status_code == 200
    payload = generate_response.json()
    assert payload["revision"] == 2
    assert payload["spec_json"]["metadata"]["version"].endswith("-gen")

    with client.app.state.db.session() as db:
        logs = list(
            db.scalars(
                select(AuthoringGenerationLogModel).where(
                    AuthoringGenerationLogModel.session_id == session_id
                )
            )
        )
    assert logs
    assert logs[-1].status == "success"
