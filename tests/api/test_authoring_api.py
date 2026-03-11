from __future__ import annotations

from fastapi.testclient import TestClient


def _valid_authoring_spec(version: str = "v1.0.0") -> dict:
    return {
        "schema_version": "pipeliner.workflow/v1alpha1",
        "metadata": {
            "workflow_id": "test_wf",
            "version": version,
            "title": "Test WF",
            "purpose": "Verify authoring flow",
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


def test_authoring_session_lifecycle(client: TestClient) -> None:
    response = client.post(
        "/api/authoring/sessions",
        json={
            "title": "Test Session",
            "intent_brief": "Create a draft workflow for content generation",
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    assert response.json()["latest_revision"] == 1

    save_response = client.post(
        f"/api/authoring/sessions/{session_id}/drafts",
        json={
            "spec": _valid_authoring_spec(),
            "instruction": "Start from a single drafting node",
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["revision"] == 2
    assert save_response.json()["graph"]["nodes"][0]["id"] == "draft_article"
    project_root = client.app.state.settings.projects_root / "test_wf"
    assert (project_root / ".claude" / "skills" / "draft-wechat-article" / "SKILL.md").exists()
    assert (
        project_root
        / ".claude"
        / "skills"
        / "review-wechat-article"
        / "references"
        / "node_context.json"
    ).exists()

    continue_response = client.post(
        f"/api/authoring/sessions/{session_id}/continue",
        json={
            "instruction": "Bump the version after refinement",
            "spec": _valid_authoring_spec(version="v1.0.1"),
        },
    )
    assert continue_response.status_code == 200
    assert continue_response.json()["revision"] == 3

    latest_response = client.get(f"/api/authoring/sessions/{session_id}/drafts/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["revision"] == 3
    assert latest_response.json()["workflow_view"]["cards"][0]["node_id"] == "draft_article"

    drafts_response = client.get(f"/api/authoring/sessions/{session_id}/drafts")
    assert drafts_response.status_code == 200
    assert [item["revision"] for item in drafts_response.json()["drafts"]] == [1, 2, 3]

    messages_response = client.get(f"/api/authoring/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert len(messages_response.json()["messages"]) >= 3

    publish_response = client.post(f"/api/authoring/sessions/{session_id}/publish?revision=3")
    assert publish_response.status_code == 200
    assert publish_response.json()["workflow_id"] == "test_wf"
    assert publish_response.json()["version"] == "v1.0.1"

    session_response = client.get(f"/api/authoring/sessions/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["published_revision"] == 3
    assert session_response.json()["published_workflow_id"] == "test_wf"


def test_publish_invalid_draft_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/authoring/sessions",
        json={"title": "Broken Draft", "intent_brief": "Try invalid publish"},
    )
    session_id = response.json()["session_id"]

    invalid_spec = _valid_authoring_spec()
    invalid_spec["nodes"][0]["validators"] = []
    save_response = client.post(
        f"/api/authoring/sessions/{session_id}/drafts",
        json={"spec": invalid_spec},
    )
    assert save_response.status_code == 200
    assert save_response.json()["lint_report"]["blocking"] is True

    publish_response = client.post(f"/api/authoring/sessions/{session_id}/publish")
    assert publish_response.status_code == 400
    assert "无法发布包含错误的 draft" in publish_response.json()["detail"]


def test_derive_graph_projection_returns_full_package(client: TestClient) -> None:
    response = client.post(
        "/api/authoring/sessions",
        json={"title": "Derive Graph", "intent_brief": "Need synchronized package"},
    )
    session_id = response.json()["session_id"]

    client.post(
        f"/api/authoring/sessions/{session_id}/drafts",
        json={"spec": _valid_authoring_spec()},
    )

    derive_response = client.get(f"/api/authoring/sessions/{session_id}/drafts/2/derive")
    assert derive_response.status_code == 200
    payload = derive_response.json()

    assert payload["graph"]["nodes"][0]["id"] == "draft_article"
    assert payload["workflow_view"]["metadata"]["workflow_id"] == "test_wf"
    assert payload["lint_report"]["blocking"] is False
