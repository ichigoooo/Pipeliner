from __future__ import annotations

from datetime import datetime, timezone


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
        },
    )
    assert response.status_code == 200
    return response.json()


def _publish_draft_artifact(
    client,
    settings,
    workspace_manager,
    run_info,
    content: str,
    version: str,
    round_no: int,
) -> None:
    artifact_rel = (
        f"{run_info['workspace_root']}/artifacts/"
        f"article_draft@{version}/payload/article.md"
    )
    artifact_path = settings.data_dir / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(content, encoding="utf-8")
    digest, size = workspace_manager.compute_digest(artifact_path)
    response = client.post(
        "/api/artifacts",
        json={
            "schema_version": "pipeliner.artifact/v1alpha1",
            "artifact_id": "article_draft",
            "version": version,
            "kind": "file",
            "produced_by": {
                "run_id": run_info["run_id"],
                "node_id": "draft_article",
                "round_no": round_no,
                "role": "executor",
            },
            "storage": {"backend": "local_fs", "uri": artifact_rel},
            "integrity": {"digest": digest, "size_bytes": size},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200


def test_callback_event_id_is_idempotent(
    client,
    workflow_fixture,
    settings,
    workspace_manager,
) -> None:
    _register_workflow(client, workflow_fixture)
    run_info = _start_run(client)
    _publish_draft_artifact(client, settings, workspace_manager, run_info, "draft v1", "v1", 1)

    payload = {
        "schema_version": "pipeliner.callback/v1alpha1",
        "event_id": "evt_exec_once",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_info["run_id"],
        "node_id": "draft_article",
        "round_no": 1,
        "actor": {"role": "executor"},
        "execution": {"status": "completed"},
        "submission": {
            "artifacts": [{"artifact_id": "article_draft", "version": "v1"}]
        },
    }

    first = client.post("/api/callbacks", json=payload)
    assert first.status_code == 200
    assert first.json()["duplicate"] is False

    second = client.post("/api/callbacks", json=payload)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    callbacks = client.get(f"/api/runs/{run_info['run_id']}/callbacks")
    assert callbacks.status_code == 200
    assert len(callbacks.json()["events"]) == 1
