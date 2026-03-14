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
            "auto_drive": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_artifact_registration_is_resolvable_and_immutable(
    client,
    workflow_fixture,
    settings,
    workspace_manager,
) -> None:
    _register_workflow(client, workflow_fixture)
    run_info = _start_run(client)
    artifact_rel = f"{run_info['workspace_root']}/artifacts/article_draft@v1/payload/article.md"
    artifact_path = settings.data_dir / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("hello world", encoding="utf-8")
    digest, size = workspace_manager.compute_digest(artifact_path)

    manifest = {
        "schema_version": "pipeliner.artifact/v1alpha1",
        "artifact_id": "article_draft",
        "version": "v1",
        "kind": "file",
        "produced_by": {
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 1,
            "role": "executor",
        },
        "storage": {
            "backend": "local_fs",
            "uri": artifact_rel,
        },
        "integrity": {
            "digest": digest,
            "size_bytes": size,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "descriptor": {
            "media_type": "text/markdown",
            "entrypoint": "article.md",
        },
    }

    response = client.post("/api/artifacts", json=manifest)
    assert response.status_code == 200
    assert response.json()["created"] is True

    response = client.get(f"/api/runs/{run_info['run_id']}/artifacts")
    assert response.status_code == 200
    assert response.json()["artifacts"][0]["artifact_id"] == "article_draft"

    artifact_path.write_text("changed content", encoding="utf-8")
    changed_digest, changed_size = workspace_manager.compute_digest(artifact_path)
    manifest["integrity"] = {"digest": changed_digest, "size_bytes": changed_size}
    conflict_response = client.post("/api/artifacts", json=manifest)
    assert conflict_response.status_code == 409
