from __future__ import annotations

from fastapi.testclient import TestClient

from pipeliner.persistence.repositories import RunRepository


def _valid_authoring_spec(version: str = "v1.0.0") -> dict:
    return {
        "schema_version": "pipeliner.workflow/v1alpha1",
        "metadata": {
            "workflow_id": "iteration_flow",
            "version": version,
            "title": "Iteration Flow",
            "purpose": "Verify iteration flow",
            "tags": ["studio"],
        },
        "inputs": [],
        "outputs": [],
        "nodes": [
            {
                "node_id": "draft_article",
                "title": "Draft Article",
                "purpose": "Draft content",
                "archetype": "draft-content",
                "depends_on": [],
                "inputs": [],
                "outputs": [
                    {
                        "name": "article_draft",
                        "shape": "markdown",
                        "summary": "Generated draft",
                    }
                ],
                "executor": {"skill": "draft-wechat-article"},
                "validators": [{"validator_id": "content-review", "skill": "review-wechat-article"}],
                "acceptance": {
                    "done_means": "Produce a coherent draft",
                    "pass_condition": ["Clear structure"],
                },
                "gate": {"mode": "all_validators_pass"},
                "handoff": {"outputs": ["article_draft"]},
            }
        ],
        "defaults": {"runtime_guards": {"timeout": "30m", "max_rework_rounds": 3}},
        "extensions": {},
    }


def test_iteration_from_version_and_run(client: TestClient) -> None:
    register_response = client.post(
        "/api/workflows/register",
        json={"spec": _valid_authoring_spec()},
    )
    assert register_response.status_code == 200

    from_version = client.post(
        "/api/authoring/sessions/from-version",
        json={"workflow_id": "iteration_flow", "version": "v1.0.0"},
    )
    assert from_version.status_code == 200
    payload = from_version.json()
    assert payload["source"]["type"] == "workflow_version"
    project_root = client.app.state.settings.projects_root / "iteration_flow"
    assert (
        project_root / ".claude" / "skills" / "draft-wechat-article" / "SKILL.md"
    ).exists()
    assert (
        project_root
        / ".claude"
        / "skills"
        / "review-wechat-article"
        / "references"
        / "node_context.json"
    ).exists()

    run_response = client.post(
        "/api/runs",
        json={"workflow_id": "iteration_flow", "version": "v1.0.0", "inputs": {}, "auto_drive": False},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        node_run = run_repo.get_latest_node_run(run_id, "draft_article")
        assert node_run is not None
        node_run.status = "blocked"
        node_run.rework_brief_json = {"summary": "need improvements"}
        db.flush()

    from_run = client.post(
        "/api/authoring/sessions/from-run",
        json={"run_id": run_id},
    )
    assert from_run.status_code == 200
    run_payload = from_run.json()
    assert run_payload["source"]["type"] == "attention_run"
    assert run_payload["source"]["payload"]["run_id"] == run_id
    assert (
        project_root / ".claude" / "skills" / "draft-wechat-article" / "SKILL.md"
    ).exists()
