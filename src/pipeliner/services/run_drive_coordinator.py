from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import threading
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.db import Database
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.services.errors import ConflictError
from pipeliner.services.run_driver import RunDriver


@dataclass(slots=True)
class DriverRecord:
    run_id: str
    status: str
    mode: str
    max_steps: int
    started_at: str
    ended_at: str | None = None
    last_error: str | None = None
    stop_reason: str | None = None
    result_status: str | None = None
    thread: threading.Thread | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "mode": self.mode,
            "max_steps": self.max_steps,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "last_error": self.last_error,
            "stop_reason": self.stop_reason,
            "result_status": self.result_status,
        }


class RunDriveCoordinator:
    def __init__(
        self,
        db: Database,
        settings: Settings | None = None,
        *,
        default_auto_max_steps: int = 500,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.default_auto_max_steps = default_auto_max_steps
        self._lock = threading.Lock()
        self._records: dict[str, DriverRecord] = {}

    def start_auto_drive(
        self,
        run_id: str,
        *,
        executor_command_template: str | None = None,
        validator_command_template: str | None = None,
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        record = self._begin_run(run_id, mode="auto", max_steps=max_steps or self.default_auto_max_steps)
        thread = threading.Thread(
            target=self._run_in_thread,
            kwargs={
                "run_id": run_id,
                "max_steps": record.max_steps,
                "executor_command_template": executor_command_template,
                "validator_command_template": validator_command_template,
            },
            daemon=True,
            name=f"pipeliner-drive-{run_id}",
        )
        record.thread = thread
        thread.start()
        return record.snapshot()

    def drive(
        self,
        run_id: str,
        *,
        max_steps: int,
        executor_command_template: str | None = None,
        validator_command_template: str | None = None,
    ) -> dict[str, Any]:
        self._begin_run(run_id, mode="manual", max_steps=max_steps)
        try:
            result = self._execute(
                run_id=run_id,
                max_steps=max_steps,
                executor_command_template=executor_command_template,
                validator_command_template=validator_command_template,
            )
        except Exception as exc:
            self._finish_failure(run_id, str(exc))
            raise
        self._finish_success(
            run_id,
            stop_reason=result.get("stop_reason"),
            result_status=result.get("status"),
        )
        return result

    def get_status(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return {
                    "run_id": run_id,
                    "status": "idle",
                    "mode": None,
                    "max_steps": None,
                    "started_at": None,
                    "ended_at": None,
                    "last_error": None,
                    "stop_reason": None,
                    "result_status": None,
                }
            return record.snapshot()

    def shutdown(self, timeout: float = 0.2) -> None:
        with self._lock:
            threads = [record.thread for record in self._records.values() if record.thread is not None]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)

    def _run_in_thread(
        self,
        *,
        run_id: str,
        max_steps: int,
        executor_command_template: str | None,
        validator_command_template: str | None,
    ) -> None:
        try:
            result = self._execute(
                run_id=run_id,
                max_steps=max_steps,
                executor_command_template=executor_command_template,
                validator_command_template=validator_command_template,
            )
        except Exception as exc:
            self._finish_failure(run_id, str(exc))
            return
        self._finish_success(
            run_id,
            stop_reason=result.get("stop_reason"),
            result_status=result.get("status"),
        )

    def _execute(
        self,
        *,
        run_id: str,
        max_steps: int,
        executor_command_template: str | None,
        validator_command_template: str | None,
    ) -> dict[str, Any]:
        with self.db.session() as session:
            driver = RunDriver(
                RunRepository(session),
                WorkflowRepository(session),
                CallbackRepository(session),
                ArtifactRepository(session),
                self.settings,
            )
            return driver.drive(
                run_id=run_id,
                executor_command_template=executor_command_template,
                validator_command_template=validator_command_template,
                max_steps=max_steps,
            )

    def _begin_run(self, run_id: str, *, mode: str, max_steps: int) -> DriverRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            current = self._records.get(run_id)
            if current is not None and current.status == "running":
                raise ConflictError(f"run {run_id} 已有 driver 在运行")
            record = DriverRecord(
                run_id=run_id,
                status="running",
                mode=mode,
                max_steps=max_steps,
                started_at=now,
            )
            self._records[run_id] = record
            return record

    def _finish_success(self, run_id: str, *, stop_reason: str | None, result_status: str | None) -> None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return
            record.status = "completed"
            record.ended_at = datetime.now(timezone.utc).isoformat()
            record.stop_reason = stop_reason
            record.result_status = result_status
            record.thread = None

    def _finish_failure(self, run_id: str, error: str) -> None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return
            record.status = "failed"
            record.ended_at = datetime.now(timezone.utc).isoformat()
            record.last_error = error
            record.thread = None
