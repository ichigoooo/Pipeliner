from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from pipeliner.app import create_app
from pipeliner.persistence.models import BatchRunItemModel, BatchRunModel
from pipeliner.persistence.repositories import RunRepository


def _register_workflow(client: TestClient, workflow_fixture: dict) -> None:
    response = client.post("/api/workflows/register", json={"spec": workflow_fixture})
    assert response.status_code == 200


def _wait_for_batch(client: TestClient, batch_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/batch-runs/{batch_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["batch"]["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"batch {batch_id} did not reach a terminal state")


def test_batch_run_template_and_detail(client: TestClient, workflow_fixture: dict, monkeypatch) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    assert template_response.status_code == 200
    template_lines = template_response.text.strip().splitlines()
    assert template_lines[0] == "topic"
    assert template_lines[1].startswith("说明:")

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha", " "]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["workflow_id"] == "mvp-review-loop"
    assert create_payload["version"] == "0.1.0"
    assert create_payload["total_count"] == 2
    assert create_payload["failed_count"] == 1

    detail_payload = _wait_for_batch(client, create_payload["batch_id"])
    assert detail_payload["batch"]["status"] == "completed"
    assert detail_payload["batch"]["success_count"] == 1
    assert detail_payload["batch"]["failed_count"] == 1
    assert len(detail_payload["items"]) == 2
    assert detail_payload["items"][0]["status"] == "completed"
    assert detail_payload["items"][0]["run_id"] is not None
    assert detail_payload["items"][1]["status"] == "failed"
    assert "缺少必填 workflow inputs" in detail_payload["items"][1]["error_message"]
    assert "topic" in detail_payload["items"][1]["error_message"]

    list_response = client.get("/api/batch-runs")
    assert list_response.status_code == 200
    batches = list_response.json()["batches"]
    assert any(item["batch_id"] == create_payload["batch_id"] for item in batches)


def test_open_run_workspace_endpoint(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    run_response = client.post(
        "/api/runs",
        json={
            "workflow_id": "mvp-review-loop",
            "version": "0.1.0",
            "inputs": {"topic": "open workspace"},
            "auto_drive": False,
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()

    opened_commands: list[list[str]] = []

    def _mock_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        opened_commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("pipeliner.services.preview_service.subprocess.run", _mock_run)

    open_response = client.post(f"/api/runs/{run_payload['run_id']}/open-folder")
    assert open_response.status_code == 200
    open_payload = open_response.json()
    assert open_payload["run_id"] == run_payload["run_id"]
    assert open_payload["opened_path"].endswith(run_payload["run_id"])
    assert opened_commands
    assert opened_commands[0][-1].endswith(run_payload["run_id"])


def test_batch_detail_marks_deleted_run_history(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha"]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["batch_id"]

    detail_payload = _wait_for_batch(client, batch_id)
    run_id = detail_payload["items"][0]["run_id"]
    assert run_id is not None

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        run_model = run_repo.get_run(run_id)
        assert run_model is not None
        run_model.status = "completed"

    delete_response = client.delete(f"/api/runs/{run_id}")
    assert delete_response.status_code == 200

    batch_response = client.get(f"/api/batch-runs/{batch_id}")
    assert batch_response.status_code == 200
    item = batch_response.json()["items"][0]
    assert item["run_id"] == run_id
    assert item["run_deleted"] is True


def test_delete_completed_batch_removes_batch_and_child_runs(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha"]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["batch_id"]

    detail_payload = _wait_for_batch(client, batch_id)
    run_id = detail_payload["items"][0]["run_id"]
    assert run_id is not None

    with client.app.state.db.session() as db:
        run_repo = RunRepository(db)
        run_model = run_repo.get_run(run_id)
        assert run_model is not None
        run_model.status = "completed"

    delete_response = client.delete(f"/api/batch-runs/{batch_id}")
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["batch_id"] == batch_id
    assert payload["deleted"] is True
    assert run_id in payload["deleted_run_ids"]

    batch_response = client.get(f"/api/batch-runs/{batch_id}")
    assert batch_response.status_code == 404

    run_response = client.get(f"/api/runs/{run_id}")
    assert run_response.status_code == 404


def test_bulk_delete_batches_removes_multiple_completed_batches(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    batch_ids: list[str] = []
    for topic in ("alpha", "beta"):
        create_response = client.post(
            "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
            files={
                "file": (
                    "inputs.csv",
                    "\n".join(template_lines + [topic]) + "\n",
                    "text/csv",
                )
            },
        )
        assert create_response.status_code == 200
        batch_id = create_response.json()["batch_id"]
        detail_payload = _wait_for_batch(client, batch_id)
        run_id = detail_payload["items"][0]["run_id"]
        assert run_id is not None
        with client.app.state.db.session() as db:
            run_repo = RunRepository(db)
            run_model = run_repo.get_run(run_id)
            assert run_model is not None
            run_model.status = "completed"
        batch_ids.append(batch_id)

    delete_response = client.post(
        "/api/batch-runs/bulk-delete",
        json={"batch_ids": batch_ids},
    )
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["deleted"] is True
    assert payload["deleted_count"] == 2
    assert payload["batch_ids"] == batch_ids

    list_response = client.get("/api/batch-runs")
    assert list_response.status_code == 200
    remaining_ids = {item["batch_id"] for item in list_response.json()["batches"]}
    assert not remaining_ids.intersection(batch_ids)


def test_delete_running_batch_is_rejected(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    monkeypatch.setattr(
        client.app.state.run_drive_coordinator,
        "start_auto_drive",
        lambda run_id, **kwargs: {"run_id": run_id, "status": "running"},
    )
    monkeypatch.setattr(
        client.app.state.batch_run_coordinator,
        "_wait_for_terminal",
        lambda run_id: ("completed", None),
    )

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha", "beta"]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["batch_id"]

    response = client.delete(f"/api/batch-runs/{batch_id}")
    assert response.status_code == 400
    assert "不允许删除" in response.json()["detail"]


def test_batch_list_does_not_reconcile_on_read(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha"]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200

    def _fail_reconcile(*args, **kwargs):
        raise AssertionError("list endpoint should not reconcile batch state")

    monkeypatch.setattr(
        "pipeliner.services.batch_run_service.BatchRunService.reconcile_batch_progress",
        _fail_reconcile,
    )

    response = client.get("/api/batch-runs")
    assert response.status_code == 200
    assert response.json()["batches"]


def test_batch_detail_does_not_reconcile_on_read(
    client: TestClient,
    workflow_fixture: dict,
    monkeypatch,
) -> None:
    _register_workflow(client, workflow_fixture)

    template_response = client.get("/api/workflows/mvp-review-loop/versions/0.1.0/inputs/template.csv")
    template_lines = template_response.text.strip().splitlines()

    create_response = client.post(
        "/api/workflows/mvp-review-loop/versions/0.1.0/batch-runs",
        files={
            "file": (
                "inputs.csv",
                "\n".join(template_lines + ["alpha"]) + "\n",
                "text/csv",
            )
        },
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["batch_id"]

    def _fail_reconcile(*args, **kwargs):
        raise AssertionError("detail endpoint should not reconcile batch state")

    monkeypatch.setattr(
        "pipeliner.services.batch_run_service.BatchRunService.reconcile_batch_progress",
        _fail_reconcile,
    )

    response = client.get(f"/api/batch-runs/{batch_id}")
    assert response.status_code == 200
    assert response.json()["batch"]["batch_id"] == batch_id


def test_startup_recovers_incomplete_batch_with_missing_run(settings) -> None:
    settings.ensure_directories()
    app = create_app(settings)
    app.state.db.create_all()
    with app.state.db.session() as session:
        batch = BatchRunModel(
            id="batch_recovery_case",
            workflow_id="mvp-review-loop",
            workflow_version="0.1.0",
            status="running",
            total_count=1,
            success_count=0,
            failed_count=0,
            started_at=datetime.now(timezone.utc),
        )
        item = BatchRunItemModel(
            batch_id=batch.id,
            row_index=1,
            inputs_json={"topic": "orphan"},
            run_id="run_missing_for_recovery",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        session.add(batch)
        session.add(item)

    with TestClient(app):
        pass

    with app.state.db.session() as session:
        recovered_batch = session.get(BatchRunModel, "batch_recovery_case")
        recovered_item = session.get(BatchRunItemModel, item.id)
        assert recovered_batch is not None
        assert recovered_item is not None
        assert recovered_batch.status == "completed"
        assert recovered_batch.failed_count == 1
        assert recovered_batch.ended_at is not None
        assert recovered_item.status == "failed"
        assert recovered_item.error_message == "run 不存在"
