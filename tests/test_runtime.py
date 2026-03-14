from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeliner.persistence.models import NodeRunModel


def _register_workflow(client, workflow_fixture) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _start_run(client) -> dict:
    response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "AI"},
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_timeout_reconcile_marks_waiting_node_as_attention(client, workflow_fixture) -> None:
    _register_workflow(client, workflow_fixture)
    run_info = _start_run(client)

    with client.app.state.db.session() as session:
        node_run = (
            session.query(NodeRunModel)
            .filter_by(
                run_id=run_info["run_id"],
                node_id="draft_article",
                round_no=1,
            )
            .one()
        )
        node_run.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)

    response = client.post("/api/runs/reconcile-timeouts")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

    detail = client.get(f"/api/runs/{run_info['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "needs_attention"
    assert detail.json()["nodes"][0]["status"] == "timed_out"
