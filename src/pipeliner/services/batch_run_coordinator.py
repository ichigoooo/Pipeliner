from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import time
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.db import Database
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    BatchRunRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.services.batch_run_service import BatchRunService
from pipeliner.services.errors import ConflictError
from pipeliner.services.run_drive_coordinator import RunDriveCoordinator
from pipeliner.types import RunStatus


@dataclass(slots=True)
class BatchRecord:
    batch_id: str
    status: str
    started_at: str
    ended_at: str | None = None
    last_error: str | None = None
    thread: threading.Thread | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "last_error": self.last_error,
        }


class BatchRunCoordinator:
    def __init__(
        self,
        db: Database,
        settings: Settings | None = None,
        *,
        poll_interval: float = 1.5,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.poll_interval = poll_interval
        self._lock = threading.Lock()
        self._records: dict[str, BatchRecord] = {}

    def start_batch(self, batch_id: str, run_drive_coordinator: RunDriveCoordinator) -> dict[str, Any]:
        record = self._begin_batch(batch_id)
        thread = threading.Thread(
            target=self._run_in_thread,
            kwargs={
                "batch_id": batch_id,
                "run_drive_coordinator": run_drive_coordinator,
            },
            daemon=True,
            name=f"pipeliner-batch-{batch_id}",
        )
        record.thread = thread
        thread.start()
        return record.snapshot()

    def recover_incomplete_batches(self) -> None:
        with self.db.session() as session:
            service = self._service(session)
            batches = service.batch_repo.list_incomplete_batches()
            for batch in batches:
                service.reconcile_batch_progress(batch.id)

    def _run_in_thread(self, *, batch_id: str, run_drive_coordinator: RunDriveCoordinator) -> None:
        try:
            self._execute(batch_id=batch_id, run_drive_coordinator=run_drive_coordinator)
        except Exception as exc:
            self._finish_failure(batch_id, str(exc))
            with self.db.session() as session:
                service = self._service(session)
                service.mark_batch_failed(batch_id, str(exc))
            return
        self._finish_success(batch_id)

    def _execute(self, *, batch_id: str, run_drive_coordinator: RunDriveCoordinator) -> None:
        with self.db.session() as session:
            service = self._service(session)
            service.mark_batch_running(batch_id)

        while True:
            with self.db.session() as session:
                service = self._service(session)
                start_result = service.start_next_item(batch_id)
                if start_result is None:
                    break
                item_id = start_result.item_id
                run_id = start_result.run_id

            if run_id is None:
                continue

            run_drive_coordinator.start_auto_drive(run_id)
            run_status, stop_reason = self._wait_for_terminal(run_id)

            with self.db.session() as session:
                service = self._service(session)
                service.finalize_item_from_run(batch_id, item_id, run_status, stop_reason)

        with self.db.session() as session:
            service = self._service(session)
            service.finalize_batch(batch_id)

    def _wait_for_terminal(self, run_id: str) -> tuple[str, str | None]:
        while True:
            with self.db.session() as session:
                run_repo = RunRepository(session)
                run = run_repo.get_run(run_id)
                if run is None:
                    return "failed", "run 不存在"
                if run.status in {
                    RunStatus.COMPLETED.value,
                    RunStatus.NEEDS_ATTENTION.value,
                    RunStatus.STOPPED.value,
                }:
                    return run.status, run.stop_reason
            time.sleep(self.poll_interval)

    def _service(self, session) -> BatchRunService:
        return BatchRunService(
            BatchRunRepository(session),
            RunRepository(session),
            WorkflowRepository(session),
            ArtifactRepository(session),
            self.settings,
        )

    def _begin_batch(self, batch_id: str) -> BatchRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            current = self._records.get(batch_id)
            if current is not None and current.status == "running":
                raise ConflictError(f"batch {batch_id} 已有任务在运行")
            record = BatchRecord(
                batch_id=batch_id,
                status="running",
                started_at=now,
            )
            self._records[batch_id] = record
            return record

    def shutdown(self, timeout: float = 0.2) -> None:
        with self._lock:
            threads = [record.thread for record in self._records.values() if record.thread is not None]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)

    def _finish_success(self, batch_id: str) -> None:
        with self._lock:
            record = self._records.get(batch_id)
            if record is None:
                return
            record.status = "completed"
            record.ended_at = datetime.now(timezone.utc).isoformat()
            record.thread = None

    def _finish_failure(self, batch_id: str, error: str) -> None:
        with self._lock:
            record = self._records.get(batch_id)
            if record is None:
                return
            record.status = "failed"
            record.ended_at = datetime.now(timezone.utc).isoformat()
            record.last_error = error
            record.thread = None
