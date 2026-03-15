from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import BatchRunItemModel, BatchRunModel
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    BatchRunRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.protocols.workflow import WorkflowInputDescriptor
from pipeliner.services.errors import NotFoundError, ValidationError
from pipeliner.services.run_service import RunService
from pipeliner.services.workflow_service import WorkflowService


@dataclass(slots=True)
class BatchRunRow:
    row_index: int
    inputs: dict[str, Any]
    error: str | None = None


@dataclass(slots=True)
class BatchRunStartResult:
    item_id: int
    run_id: str | None
    error: str | None = None


class BatchRunService:
    def __init__(
        self,
        batch_repo: BatchRunRepository,
        run_repo: RunRepository,
        workflow_repo: WorkflowRepository,
        artifact_repo: ArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self.batch_repo = batch_repo
        self.run_repo = run_repo
        self.workflow_repo = workflow_repo
        self.artifact_repo = artifact_repo
        self.settings = settings or get_settings()
        self.workflow_service = WorkflowService(workflow_repo)
        self.run_service = RunService(run_repo, workflow_repo, artifact_repo, self.settings)

    def build_template_csv(self, workflow_id: str, version: str) -> str:
        spec = self.workflow_service.load_spec_model(workflow_id, version)
        headers = [item.name for item in spec.inputs]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        return buffer.getvalue()

    def parse_csv_inputs(
        self,
        workflow_id: str,
        version: str,
        content: str,
    ) -> list[BatchRunRow]:
        spec = self.workflow_service.load_spec_model(workflow_id, version)
        descriptors = {item.name: item.normalized_descriptor() for item in spec.inputs}
        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames is None:
            raise ValidationError("CSV 缺少表头")

        rows: list[BatchRunRow] = []
        for row_index, row in enumerate(reader, start=1):
            inputs: dict[str, Any] = {}
            errors: list[str] = []
            for name, descriptor in descriptors.items():
                raw = row.get(name)
                if raw is None:
                    continue
                raw_text = str(raw)
                if not raw_text.strip():
                    continue
                try:
                    inputs[name] = self._parse_value(descriptor, raw_text.strip())
                except ValueError as exc:
                    errors.append(str(exc))

            error: str | None = None
            if errors:
                error = "；".join(errors)
            else:
                try:
                    inputs = self.workflow_service.validate_run_inputs(spec, inputs)
                except ValidationError as exc:
                    error = str(exc)

            rows.append(BatchRunRow(row_index=row_index, inputs=inputs, error=error))

        return rows

    def create_batch(self, workflow_id: str, version: str, rows: list[BatchRunRow]) -> BatchRunModel:
        batch_id = self._generate_batch_id()
        failed_count = sum(1 for row in rows if row.error)
        batch = BatchRunModel(
            id=batch_id,
            workflow_id=workflow_id,
            workflow_version=version,
            status="pending",
            total_count=len(rows),
            success_count=0,
            failed_count=failed_count,
        )
        self.batch_repo.create_batch(batch)

        items = [
            BatchRunItemModel(
                batch_id=batch_id,
                row_index=row.row_index,
                inputs_json=row.inputs,
                status="failed" if row.error else "pending",
                error_message=row.error,
                ended_at=self._now() if row.error else None,
            )
            for row in rows
        ]
        self.batch_repo.create_items(items)
        return batch

    def get_batch_or_404(self, batch_id: str) -> BatchRunModel:
        batch = self.batch_repo.get_batch(batch_id)
        if batch is None:
            raise NotFoundError(f"未找到 batch: {batch_id}")
        return batch

    def list_batch_items(self, batch_id: str) -> list[BatchRunItemModel]:
        return self.batch_repo.list_items(batch_id)

    def mark_batch_running(self, batch_id: str) -> BatchRunModel:
        batch = self.get_batch_or_404(batch_id)
        if batch.status != "running":
            batch.status = "running"
            batch.started_at = batch.started_at or self._now()
        return batch

    def mark_batch_failed(self, batch_id: str, message: str) -> BatchRunModel:
        batch = self.get_batch_or_404(batch_id)
        batch.status = "failed"
        batch.error_message = message
        batch.ended_at = self._now()
        return batch

    def finalize_batch(self, batch_id: str) -> BatchRunModel:
        batch = self.get_batch_or_404(batch_id)
        if batch.status not in {"completed", "failed"}:
            batch.status = "completed"
            batch.ended_at = self._now()
        return batch

    def start_next_item(self, batch_id: str) -> BatchRunStartResult | None:
        batch = self.get_batch_or_404(batch_id)
        item = self.batch_repo.get_next_pending_item(batch_id)
        if item is None:
            return None
        try:
            run = self.run_service.start_run(
                batch.workflow_id,
                batch.workflow_version,
                item.inputs_json,
            )
        except Exception as exc:
            item.status = "failed"
            item.error_message = str(exc)
            item.ended_at = self._now()
            batch.failed_count += 1
            return BatchRunStartResult(item_id=item.id, run_id=None, error=str(exc))

        item.status = "running"
        item.run_id = run.id
        item.started_at = self._now()
        batch.status = "running"
        batch.started_at = batch.started_at or self._now()
        return BatchRunStartResult(item_id=item.id, run_id=run.id)

    def finalize_item_from_run(
        self,
        batch_id: str,
        item_id: int,
        run_status: str,
        stop_reason: str | None,
    ) -> BatchRunItemModel:
        batch = self.get_batch_or_404(batch_id)
        item = self.batch_repo.get_item(item_id)
        if item is None:
            raise NotFoundError(f"未找到 batch item: {item_id}")
        if item.status in {"completed", "failed"}:
            return item

        if run_status == "completed":
            item.status = "completed"
            batch.success_count += 1
        else:
            item.status = "failed"
            batch.failed_count += 1
            item.error_message = stop_reason or f"run 状态异常: {run_status}"

        item.ended_at = self._now()
        return item

    @staticmethod
    def _generate_batch_id() -> str:
        return f"batch_{uuid4().hex[:16]}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _parse_value(self, descriptor: WorkflowInputDescriptor, raw: str) -> Any:
        input_type = descriptor.input_type
        if input_type == "number":
            if re.fullmatch(r"[-+]?\d+", raw):
                return int(raw)
            try:
                return float(raw)
            except ValueError as exc:
                raise ValueError(f"{descriptor.name} 必须是数字") from exc
        if input_type == "boolean":
            normalized = raw.strip().lower()
            if normalized in {"true", "1"}:
                return True
            if normalized in {"false", "0"}:
                return False
            raise ValueError(f"{descriptor.name} 必须是布尔值")
        if input_type == "json":
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{descriptor.name} 必须是合法 JSON") from exc
        return raw
