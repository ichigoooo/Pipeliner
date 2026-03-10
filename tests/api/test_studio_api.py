from __future__ import annotations

from fastapi.testclient import TestClient


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client: TestClient) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "studio api test"},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_workflow_and_run_studio_endpoints(client: TestClient, workflow_fixture: dict) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)

    workflows_response = client.get("/api/workflows")
    assert workflows_response.status_code == 200
    assert workflows_response.json()["workflows"][0]["workflow_id"] == "mvp-review-loop"

    versions_response = client.get("/api/workflows/mvp-review-loop/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()["versions"][0]["version"] == "0.1.0"

    workflow_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0")
    assert workflow_response.status_code == 200
    assert workflow_response.json()["graph"]["nodes"]
    assert workflow_response.json()["workflow_view"]["cards"]

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["runs"][0]["run_id"] == run["run_id"]

    overview_response = client.get(f"/api/runs/{run['run_id']}/debug/overview")
    assert overview_response.status_code == 200
    assert overview_response.json()["timeline"][0]["node_id"] == "draft_article"

    round_response = client.get(
        f"/api/runs/{run['run_id']}/debug/nodes/draft_article/rounds/1"
    )
    assert round_response.status_code == 200
    assert round_response.json()["context"]["node"]["node_id"] == "draft_article"
    assert round_response.json()["log_refs"]


def test_attention_retry_and_settings_snapshot(
    client: TestClient,
    workflow_fixture: dict,
) -> None:
    _register_workflow(client, workflow_fixture)
    run = _start_run(client)

    dispatch_response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/executor/dispatch",
        json={"command_template": "definitely_not_existing_command"},
    )
    assert dispatch_response.status_code == 200

    attention_response = client.get("/api/runs/attention")
    assert attention_response.status_code == 200
    assert attention_response.json()["runs"][0]["run_id"] == run["run_id"]
    assert "retry_node" in attention_response.json()["runs"][0]["actions"]

    retry_response = client.post(
        f"/api/runs/{run['run_id']}/nodes/draft_article/retry",
        json={"rework_brief": {"summary": "retry from studio"}},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["round_no"] == 2
    assert retry_response.json()["waiting_for_role"] == "executor"

    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200
    payload = settings_response.json()["settings"]
    assert payload["executor_command"]["source"] in {"default", "env"}
    assert payload["storage"]["backend"]["value"] == "local_fs"
    assert payload["runtime_guards"]["default_timeout"]["value"] == "30m"
    assert isinstance(payload["skills"], list)
