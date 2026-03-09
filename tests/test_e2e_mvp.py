from __future__ import annotations

from datetime import datetime, timezone


def _publish_artifact(client, settings, workspace_manager, run_info, node_id, artifact_id, version, round_no, content) -> None:
    artifact_rel = f"{run_info['workspace_root']}/artifacts/{artifact_id}@{version}/payload/{artifact_id}.md"
    artifact_path = settings.data_dir / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(content, encoding="utf-8")
    digest, size = workspace_manager.compute_digest(artifact_path)
    response = client.post(
        "/api/artifacts",
        json={
            "schema_version": "pipeliner.artifact/v1alpha1",
            "artifact_id": artifact_id,
            "version": version,
            "kind": "file",
            "produced_by": {
                "run_id": run_info["run_id"],
                "node_id": node_id,
                "round_no": round_no,
                "role": "executor"
            },
            "storage": {"backend": "local_fs", "uri": artifact_rel},
            "integrity": {"digest": digest, "size_bytes": size},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    )
    assert response.status_code == 200


def test_mvp_e2e_review_loop_hits_revise_then_blocked(client, workflow_fixture, settings, workspace_manager) -> None:
    register_response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert register_response.status_code == 200

    run_response = client.post(
        "/api/runs",
        json={"workflow_id": "mvp-review-loop", "version": "0.1.0", "inputs": {"topic": "AI agents"}},
    )
    assert run_response.status_code == 200
    run_info = run_response.json()

    _publish_artifact(client, settings, workspace_manager, run_info, "draft_article", "article_draft", "v1", 1, "draft v1")
    exec_round_1 = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_exec_round_1",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 1,
            "actor": {"role": "executor"},
            "execution": {"status": "completed"},
            "submission": {"artifacts": [{"artifact_id": "article_draft", "version": "v1"}]}
        },
    )
    assert exec_round_1.status_code == 200

    revise_response = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_val_revise_round_1",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 1,
            "actor": {"role": "validator", "validator_id": "content-review"},
            "execution": {"status": "completed"},
            "verdict": {
                "status": "revise",
                "target_artifacts": [{"artifact_id": "article_draft", "version": "v1"}],
                "summary": "Need clearer structure"
            },
            "rework_brief": {
                "must_fix": [{"target": "title", "problem": "weak", "expected": "clearer"}],
                "preserve": ["tone"],
                "resubmit_instruction": "submit a stronger draft"
            }
        },
    )
    assert revise_response.status_code == 200

    run_after_revise = client.get(f"/api/runs/{run_info['run_id']}")
    assert run_after_revise.status_code == 200
    draft_rounds = [node for node in run_after_revise.json()["nodes"] if node["node_id"] == "draft_article"]
    assert {item["round_no"] for item in draft_rounds} == {1, 2}
    assert any(item["status"] == "waiting_executor" for item in draft_rounds)

    _publish_artifact(client, settings, workspace_manager, run_info, "draft_article", "article_draft", "v2", 2, "draft v2")
    exec_round_2 = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_exec_round_2",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 2,
            "actor": {"role": "executor"},
            "execution": {"status": "completed"},
            "submission": {"artifacts": [{"artifact_id": "article_draft", "version": "v2"}]}
        },
    )
    assert exec_round_2.status_code == 200

    pass_response = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_val_pass_round_2",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "draft_article",
            "round_no": 2,
            "actor": {"role": "validator", "validator_id": "content-review"},
            "execution": {"status": "completed"},
            "verdict": {
                "status": "pass",
                "target_artifacts": [{"artifact_id": "article_draft", "version": "v2"}],
                "summary": "Looks good"
            }
        },
    )
    assert pass_response.status_code == 200

    detail_after_pass = client.get(f"/api/runs/{run_info['run_id']}")
    assert detail_after_pass.status_code == 200
    assert any(node["node_id"] == "final_review" and node["status"] == "waiting_executor" for node in detail_after_pass.json()["nodes"])

    _publish_artifact(client, settings, workspace_manager, run_info, "final_review", "approved_article", "v1", 1, "final article")
    final_exec = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_final_exec_1",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "final_review",
            "round_no": 1,
            "actor": {"role": "executor"},
            "execution": {"status": "completed"},
            "submission": {"artifacts": [{"artifact_id": "approved_article", "version": "v1"}]}
        },
    )
    assert final_exec.status_code == 200

    blocked_response = client.post(
        "/api/callbacks",
        json={
            "schema_version": "pipeliner.callback/v1alpha1",
            "event_id": "evt_final_blocked_1",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_info["run_id"],
            "node_id": "final_review",
            "round_no": 1,
            "actor": {"role": "validator", "validator_id": "final-gate"},
            "execution": {"status": "completed"},
            "verdict": {
                "status": "blocked",
                "target_artifacts": [{"artifact_id": "approved_article", "version": "v1"}],
                "summary": "Need manual legal review"
            }
        },
    )
    assert blocked_response.status_code == 200

    final_detail = client.get(f"/api/runs/{run_info['run_id']}")
    assert final_detail.status_code == 200
    assert final_detail.json()["run"]["status"] == "needs_attention"
    assert any(node["node_id"] == "final_review" and node["status"] == "blocked" for node in final_detail.json()["nodes"])
