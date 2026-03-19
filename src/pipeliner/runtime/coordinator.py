from __future__ import annotations

import json
from datetime import timezone
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import CallbackEventModel, NodeRunModel, RunModel
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.protocols.artifact import ArtifactManifest
from pipeliner.protocols.callback import NodeCallbackPayload
from pipeliner.protocols.workflow import WorkflowNodeSpec, WorkflowSpec
from pipeliner.runtime.guards import is_timeout_exceeded
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from pipeliner.services.run_service import RunService
from pipeliner.types import ActorRole, ExecutionStatus, NodeRunStatus, RunStatus, VerdictStatus


class RuntimeCoordinator:
    def __init__(
        self,
        run_repo: RunRepository,
        workflow_repo: WorkflowRepository,
        callback_repo: CallbackRepository,
        artifact_repo: ArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.workflow_repo = workflow_repo
        self.callback_repo = callback_repo
        self.artifact_repo = artifact_repo
        self.settings = settings or get_settings()
        self.run_service = RunService(run_repo, workflow_repo, artifact_repo, self.settings)
        self.artifact_service = ArtifactService(artifact_repo, run_repo, self.settings)

    def submit_callback(self, payload: NodeCallbackPayload) -> dict:
        existing = self.callback_repo.get_event(payload.event_id)
        if existing is not None:
            return {"duplicate": True, "event_id": existing.event_id}

        run = self.run_service.get_run(payload.run_id)
        if run.status == RunStatus.STOPPED.value:
            raise InvalidStateError("run 已手动停止，拒绝新的 callback")
        spec = self.run_service.get_run_spec(run)
        node = next((item for item in spec.nodes if item.node_id == payload.node_id), None)
        if node is None:
            raise NotFoundError(f"未找到节点: {payload.node_id}")
        node_run = self.run_repo.get_node_run(run.id, payload.node_id, payload.round_no)
        if node_run is None:
            raise NotFoundError(
                "未找到 node round: "
                f"run={run.id} node={payload.node_id} round={payload.round_no}"
            )

        if payload.actor.role == ActorRole.VALIDATOR and payload.actor.validator_id:
            duplicate_validator_event = self.callback_repo.get_validator_round_event(
                run.id,
                payload.node_id,
                payload.round_no,
                payload.actor.validator_id,
            )
            if duplicate_validator_event is not None:
                raise ConflictError("同一 validator 在同一轮次已提交结果")

        event = self.callback_repo.create_event(
            CallbackEventModel(
                event_id=payload.event_id,
                run_id=payload.run_id,
                node_id=payload.node_id,
                round_no=payload.round_no,
                actor_role=payload.actor.role.value,
                validator_id=payload.actor.validator_id,
                execution_status=payload.execution.status.value,
                verdict_status=payload.verdict.status.value if payload.verdict else None,
                payload_json=payload.model_dump(mode="json"),
            )
        )
        workspace = self.run_service.get_workspace(run)
        self.run_service.workspace.write_callback_archive(
            workspace,
            payload.event_id,
            payload.model_dump(mode="json"),
        )

        if payload.actor.role == ActorRole.EXECUTOR:
            self._handle_executor_callback(run, spec, node, node_run, payload)
        else:
            self._handle_validator_callback(run, spec, node, node_run, payload)

        self.run_service.refresh_run_status(run.id)
        return {"duplicate": False, "event_id": event.event_id, "run_status": run.status}

    def reconcile_timeouts(self) -> list[dict]:
        timed_out: list[dict] = []
        waiting_statuses = {
            NodeRunStatus.WAITING_EXECUTOR.value,
            NodeRunStatus.WAITING_VALIDATOR.value,
        }
        for run in self.run_repo.list_runs():
            if run.status in {RunStatus.COMPLETED.value, RunStatus.STOPPED.value}:
                continue
            spec = self.run_service.get_run_spec(run)
            guards = spec.runtime_guards_or_default()
            latest = self.run_repo.list_latest_node_runs(run.id)
            for node_run in latest.values():
                if node_run.status not in waiting_statuses:
                    continue
                call_map = self.run_service._read_round_claude_calls(
                    self.run_service.get_workspace(run),
                    node_run.node_id,
                    node_run.round_no,
                )
                stale_issue = self._reconcile_pending_call_issue(run, node_run, call_map)
                if stale_issue is not None:
                    continue
                updated_at = node_run.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if is_timeout_exceeded(updated_at, guards):
                    node_run.status = NodeRunStatus.TIMED_OUT.value
                    node_run.stop_reason = "timeout guard exceeded"
                    node_run.waiting_for_role = None
                    run.status = RunStatus.NEEDS_ATTENTION.value
                    timed_out.append(
                        {
                            "run_id": run.id,
                            "node_id": node_run.node_id,
                            "round_no": node_run.round_no,
                        }
                    )
        return timed_out

    def reconcile_archived_callbacks(self, run_id: str) -> dict[str, list[dict[str, str]]]:
        run = self.run_service.get_run(run_id)
        workspace = self.run_service.get_workspace(run)
        callback_paths = sorted(
            workspace.callbacks_dir.glob("*.json"),
            key=lambda path: self._callback_sort_key(path),
        )
        repaired: list[dict[str, str]] = []
        failed: list[dict[str, str]] = []

        for path in callback_paths:
            try:
                payload = NodeCallbackPayload.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception as exc:
                failed.append({"event_id": path.stem, "error": str(exc)})
                continue

            if self.callback_repo.get_event(payload.event_id) is not None:
                continue

            try:
                self._reconcile_artifacts_for_callback(run, payload)
                result = self.submit_callback(payload)
            except Exception as exc:
                self.callback_repo.session.rollback()
                failed.append({"event_id": payload.event_id, "error": str(exc)})
                continue

            repaired.append(
                {
                    "event_id": payload.event_id,
                    "run_status": str(result.get("run_status") or ""),
                }
            )

        return {"repaired": repaired, "failed": failed}

    def reconcile_stale_claude_calls(self, run_id: str) -> list[dict[str, str]]:
        run = self.run_service.get_run(run_id)
        if run.status in {RunStatus.COMPLETED.value, RunStatus.STOPPED.value}:
            return []
        workspace = self.run_service.get_workspace(run)
        latest = self.run_repo.list_latest_node_runs(run.id)
        issues: list[dict[str, str]] = []

        for node_run in latest.values():
            call_map = self.run_service._read_round_claude_calls(
                workspace,
                node_run.node_id,
                node_run.round_no,
            )
            if node_run.status in {
                NodeRunStatus.WAITING_EXECUTOR.value,
                NodeRunStatus.TIMED_OUT.value,
            }:
                issue = self._reconcile_executor_call_issue(run, node_run, call_map)
                if issue is not None:
                    issues.append(issue)
                    continue
            if node_run.status in {
                NodeRunStatus.WAITING_VALIDATOR.value,
                NodeRunStatus.TIMED_OUT.value,
            }:
                issue = self._reconcile_validator_call_issue(run, node_run, call_map)
                if issue is not None:
                    issues.append(issue)

        if issues:
            self.run_service.refresh_run_status(run.id)
        return issues

    def _handle_executor_callback(
        self,
        run: RunModel,
        spec: WorkflowSpec,
        node: WorkflowNodeSpec,
        node_run: NodeRunModel,
        payload: NodeCallbackPayload,
    ) -> None:
        if node_run.status != NodeRunStatus.WAITING_EXECUTOR.value:
            raise InvalidStateError("当前节点轮次不在等待 executor 状态")
        if payload.execution.status == ExecutionStatus.COMPLETED:
            submission = payload.submission
            if submission is None or not submission.artifacts:
                raise ValidationError("executor callback 必须提交至少一个 artifact ref")
            expected_outputs = set(node.handoff.outputs or [item.name for item in node.outputs])
            submitted_outputs = {item.artifact_id for item in submission.artifacts}
            if not expected_outputs.issubset(submitted_outputs):
                raise ValidationError(
                    "executor callback 缺少节点 handoff.outputs 对应的 artifact"
                )
            for artifact_ref in submission.artifacts:
                self.artifact_service.resolve_ref(run.id, artifact_ref)
            node_run.status = NodeRunStatus.WAITING_VALIDATOR.value
            node_run.waiting_for_role = "validator"
            validator_context = self.run_service.build_validator_context(
                run,
                node,
                node_run.round_no,
                submission.artifacts,
            )
            workspace = self.run_service.get_workspace(run)
            for validator in node.validators:
                self.run_service.workspace.write_validator_context(
                    workspace,
                    node.node_id,
                    node_run.round_no,
                    validator.validator_id,
                    {
                        **validator_context,
                        "validator": validator.model_dump(mode="json"),
                    },
                )
            return
        if payload.execution.status == ExecutionStatus.FAILED:
            node_run.status = NodeRunStatus.FAILED.value
            node_run.stop_reason = payload.execution.message or "executor failed"
            node_run.waiting_for_role = None
            run.status = RunStatus.NEEDS_ATTENTION.value
            return
        if payload.execution.status == ExecutionStatus.TIMEOUT:
            node_run.status = NodeRunStatus.TIMED_OUT.value
            node_run.stop_reason = payload.execution.message or "executor timeout"
            node_run.waiting_for_role = None
            run.status = RunStatus.NEEDS_ATTENTION.value
            return

    def _handle_validator_callback(
        self,
        run: RunModel,
        spec: WorkflowSpec,
        node: WorkflowNodeSpec,
        node_run: NodeRunModel,
        payload: NodeCallbackPayload,
    ) -> None:
        if node_run.status != NodeRunStatus.WAITING_VALIDATOR.value:
            raise InvalidStateError("当前节点轮次不在等待 validator 状态")
        if payload.execution.status == ExecutionStatus.FAILED:
            node_run.status = NodeRunStatus.FAILED.value
            node_run.stop_reason = payload.execution.message or "validator failed"
            node_run.waiting_for_role = None
            run.status = RunStatus.NEEDS_ATTENTION.value
            return
        if payload.execution.status == ExecutionStatus.TIMEOUT:
            node_run.status = NodeRunStatus.TIMED_OUT.value
            node_run.stop_reason = payload.execution.message or "validator timeout"
            node_run.waiting_for_role = None
            run.status = RunStatus.NEEDS_ATTENTION.value
            return

        verdict = payload.verdict
        if verdict is None:
            raise ValidationError("validator callback 缺少 verdict")
        if verdict.status == VerdictStatus.BLOCKED:
            node_run.status = NodeRunStatus.BLOCKED.value
            node_run.stop_reason = verdict.summary or "validator blocked"
            node_run.waiting_for_role = None
            run.status = RunStatus.NEEDS_ATTENTION.value
            return
        if verdict.status == VerdictStatus.REVISE:
            guards = spec.runtime_guards_or_default()
            max_rework_rounds = max(
                guards.max_rework_rounds,
                self.settings.default_max_rework_rounds,
            )
            next_round = node_run.round_no + 1
            if next_round > max_rework_rounds:
                node_run.status = NodeRunStatus.REWORK_LIMIT.value
                node_run.stop_reason = "exceeded max_rework_rounds"
                node_run.waiting_for_role = None
                run.status = RunStatus.NEEDS_ATTENTION.value
                return
            node_run.status = NodeRunStatus.REVISE.value
            node_run.stop_reason = verdict.summary or "validator requested revise"
            node_run.waiting_for_role = None
            workspace = self.run_service.get_workspace(run)
            self.run_service._create_node_round(
                run,
                spec,
                node,
                next_round,
                workspace,
                rework_brief=(
                    payload.rework_brief.model_dump(mode="json")
                    if payload.rework_brief
                    else None
                ),
            )
            return

        events = self.callback_repo.list_node_round_events(run.id, node.node_id, node_run.round_no)
        validator_passes = {
            event.validator_id
            for event in events
            if (
                event.actor_role == ActorRole.VALIDATOR.value
                and event.verdict_status == VerdictStatus.PASS.value
            )
        }
        expected = {validator.validator_id for validator in node.validators}
        if expected.issubset(validator_passes):
            node_run.status = NodeRunStatus.PASSED.value
            node_run.waiting_for_role = None
            self.run_service.activate_ready_nodes(run.id)

    def _reconcile_artifacts_for_callback(
        self,
        run: RunModel,
        payload: NodeCallbackPayload,
    ) -> None:
        if payload.actor.role != ActorRole.EXECUTOR or payload.submission is None:
            return

        workspace = self.run_service.get_workspace(run)
        for ref in payload.submission.artifacts:
            if self.artifact_repo.get_artifact(run.id, ref.artifact_id, ref.version) is not None:
                continue
            manifest_path = self.run_service.workspace.artifact_manifest_path(
                workspace,
                ref.artifact_id,
                ref.version,
            )
            if not manifest_path.exists():
                raise NotFoundError(f"缺少 artifact manifest: {ref.artifact_id}@{ref.version}")
            manifest = ArtifactManifest.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
            self.artifact_service.publish_manifest(manifest)

    @staticmethod
    def _callback_sort_key(path) -> str:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return path.name
        sent_at = payload.get("sent_at")
        if isinstance(sent_at, str) and sent_at:
            return sent_at
        return path.name

    def _reconcile_executor_call_issue(
        self,
        run: RunModel,
        node_run: NodeRunModel,
        call_map: dict[str, Any],
    ) -> dict[str, str] | None:
        call_id = call_map.get("executor_call_id")
        call_meta = call_map.get("executor_call")
        if not call_id or not isinstance(call_meta, dict):
            return None
        status = call_meta.get("status")
        if status == "failed":
            message = str(call_meta.get("error_message") or "executor call failed")
            node_run.status = NodeRunStatus.FAILED.value
            node_run.waiting_for_role = None
            node_run.stop_reason = message
            run.status = RunStatus.NEEDS_ATTENTION.value
            run.stop_reason = message
            return {
                "node_id": node_run.node_id,
                "round_no": str(node_run.round_no),
                "reason": message,
            }
        return None

    def _reconcile_validator_call_issue(
        self,
        run: RunModel,
        node_run: NodeRunModel,
        call_map: dict[str, Any],
    ) -> dict[str, str] | None:
        for validator_call in call_map.get("validator_calls", []):
            validator_id = validator_call.get("validator_id")
            if not validator_id:
                continue
            existing = self.callback_repo.get_validator_round_event(
                run.id,
                node_run.node_id,
                node_run.round_no,
                validator_id,
            )
            if existing is not None:
                continue
            call_meta = validator_call.get("meta")
            if not isinstance(call_meta, dict):
                continue
            if call_meta.get("status") != "failed":
                continue
            message = str(call_meta.get("error_message") or f"validator {validator_id} call failed")
            node_run.status = NodeRunStatus.FAILED.value
            node_run.waiting_for_role = None
            node_run.stop_reason = message
            run.status = RunStatus.NEEDS_ATTENTION.value
            run.stop_reason = message
            return {
                "node_id": node_run.node_id,
                "round_no": str(node_run.round_no),
                "reason": message,
            }
        return None

    def _reconcile_pending_call_issue(
        self,
        run: RunModel,
        node_run: NodeRunModel,
        call_map: dict[str, Any],
    ) -> dict[str, str] | None:
        if node_run.status == NodeRunStatus.WAITING_EXECUTOR.value:
            return self._reconcile_executor_call_issue(run, node_run, call_map)
        if node_run.status == NodeRunStatus.WAITING_VALIDATOR.value:
            return self._reconcile_validator_call_issue(run, node_run, call_map)
        return None
