from __future__ import annotations

from fastapi.testclient import TestClient


def _authoring_spec(version: str = "v0.1.0") -> dict:
    return {
        "schema_version": "pipeliner.workflow/v1alpha1",
        "metadata": {
            "workflow_id": "studio_e2e",
            "version": version,
            "title": "Studio E2E",
            "purpose": "Verify developer workflow",
            "tags": ["studio"],
        },
        "inputs": [
            {
                "name": "topic",
                "shape": "string",
                "required": True,
                "summary": "Topic to write about",
            }
        ],
        "outputs": [
            {
                "name": "article",
                "from": {"node_id": "draft_article", "output": "article_draft"},
                "shape": "markdown",
                "required": True,
                "summary": "Draft article",
            }
        ],
        "nodes": [
            {
                "node_id": "draft_article",
                "title": "Draft Article",
                "purpose": "Create a first draft",
                "archetype": "draft-content",
                "depends_on": [],
                "inputs": [
                    {
                        "name": "topic",
                        "from": {"kind": "workflow_input", "name": "topic"},
                        "shape": "string",
                        "required": True,
                        "summary": "Topic context",
                    }
                ],
                "outputs": [
                    {
                        "name": "article_draft",
                        "shape": "markdown",
                        "summary": "Generated draft",
                    }
                ],
                "executor": {"skill": "draft-wechat-article"},
                "validators": [
                    {
                        "validator_id": "content-review",
                        "skill": "review-wechat-article",
                    }
                ],
                "acceptance": {
                    "done_means": "Produce a coherent draft",
                    "pass_condition": ["Clear structure"],
                },
                "gate": {"mode": "all_validators_pass"},
                "handoff": {"outputs": ["article_draft"]},
            }
        ],
        "defaults": {
            "runtime_guards": {
                "timeout": "30m",
                "max_rework_rounds": 3,
            }
        },
        "extensions": {},
    }


def test_developer_workflow_end_to_end(client: TestClient) -> None:
    session_response = client.post(
        "/api/authoring/sessions",
        json={
            "title": "Studio E2E",
            "intent_brief": "Author a workflow and verify the studio flow.",
        },
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    save_response = client.post(
        f"/api/authoring/sessions/{session_id}/drafts",
        json={"spec": _authoring_spec()},
    )
    assert save_response.status_code == 200

    publish_response = client.post(f"/api/authoring/sessions/{session_id}/publish")
    assert publish_response.status_code == 200
    workflow_id = publish_response.json()["workflow_id"]
    version = publish_response.json()["version"]

    run_response = client.post(
        "/api/runs",
        json={
            "workflow_id": workflow_id,
            "version": version,
            "inputs": {"topic": "studio e2e"},
        },
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    overview_response = client.get(f"/api/runs/{run_id}/debug/overview")
    assert overview_response.status_code == 200
    timeline = overview_response.json()["timeline"]
    assert timeline
    node_id = timeline[0]["node_id"]
    round_no = timeline[0]["round_no"]

    round_response = client.get(
        f"/api/runs/{run_id}/debug/nodes/{node_id}/rounds/{round_no}"
    )
    assert round_response.status_code == 200
    assert round_response.json()["node_id"] == node_id

    dispatch_response = client.post(
        f"/api/runs/{run_id}/nodes/{node_id}/executor/dispatch",
        json={"command_template": "definitely_not_existing_command"},
    )
    assert dispatch_response.status_code == 200

    attention_response = client.get("/api/runs/attention")
    assert attention_response.status_code == 200
    assert any(item["run_id"] == run_id for item in attention_response.json()["runs"])

    retry_response = client.post(
        f"/api/runs/{run_id}/nodes/{node_id}/retry",
        json={"rework_brief": {"summary": "retry from e2e"}},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["round_no"] >= 2
