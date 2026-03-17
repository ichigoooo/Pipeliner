from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import NodeRunModel, RunModel
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.protocols.artifact import ArtifactManifest, ArtifactRef
from pipeliner.protocols.workflow import WorkflowNodeSpec, WorkflowSpec
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.claude_call import ClaudeCallStore
from pipeliner.services.errors import InvalidStateError, NotFoundError, ValidationError
from pipeliner.services.workflow_service import WorkflowService
from pipeliner.storage.local_fs import RunWorkspace, WorkspaceManager
from pipeliner.types import NodeRunStatus, RunStatus


class RunService:
    def __init__(
        self,
        run_repo: RunRepository,
        workflow_repo: WorkflowRepository,
        artifact_repo: ArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.workflow_service = WorkflowService(workflow_repo)
        self.settings = settings or get_settings()
        self.workspace = WorkspaceManager(self.settings)
        self.artifact_service = ArtifactService(artifact_repo, run_repo, self.settings)
        self.callback_repo = CallbackRepository(run_repo.session)

    def start_run(self, workflow_id: str, version: str, inputs: dict) -> RunModel:
        spec = self.workflow_service.load_spec_model(workflow_id, version)
        inputs = self.workflow_service.validate_run_inputs(spec, inputs)
        run_id = self._generate_run_id()
        workspace = self.workspace.create_run_workspace(workflow_id, run_id)
        run = self.run_repo.create_run(
            RunModel(
                id=run_id,
                workflow_version_id=self.workflow_service.get_version(workflow_id, version).id,
                workflow_id=workflow_id,
                workflow_version=version,
                status=RunStatus.RUNNING.value,
                inputs_json=inputs,
                workspace_root=workspace.relative_root,
            )
        )
        self.workspace.write_workflow_inputs(workspace, inputs)
        self._activate_root_nodes(run, spec, workspace)
        return run

    def stop_run(self, run_id: str, reason: str = "manual_stop") -> RunModel:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise NotFoundError(f"未找到 run: {run_id}")
        run.status = RunStatus.STOPPED.value
        run.stop_reason = reason
        latest = self.run_repo.list_latest_node_runs(run.id)
        for node_run in latest.values():
            if node_run.status in {
                NodeRunStatus.WAITING_EXECUTOR.value,
                NodeRunStatus.WAITING_VALIDATOR.value,
            }:
                node_run.status = NodeRunStatus.STOPPED.value
                node_run.stop_reason = reason
        return run

    def get_run(self, run_id: str) -> RunModel:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise NotFoundError(f"未找到 run: {run_id}")
        return run

    def delete_run(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run.status == RunStatus.RUNNING.value:
            raise InvalidStateError("运行中 run 不允许删除")
        batch_id = self.run_repo.get_batch_id(run.id)
        payload = {
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "batch_id": batch_id,
            "workspace_root": run.workspace_root,
            "deleted": True,
        }
        self.run_repo.session.delete(run)
        self.run_repo.session.flush()
        self.workspace.delete_run_workspace(run.workflow_id, run.id)
        return payload

    def get_run_spec(self, run: RunModel) -> WorkflowSpec:
        return self.workflow_service.load_spec_model(run.workflow_id, run.workflow_version)

    def get_workspace(self, run: RunModel) -> RunWorkspace:
        return self.workspace.get_workspace(run.workflow_id, run.id)

    def refresh_run_status(self, run_id: str) -> RunModel:
        run = self.get_run(run_id)
        spec = self.get_run_spec(run)
        latest = self.run_repo.list_latest_node_runs(run.id)

        attention_statuses = {
            NodeRunStatus.BLOCKED.value,
            NodeRunStatus.FAILED.value,
            NodeRunStatus.TIMED_OUT.value,
            NodeRunStatus.REWORK_LIMIT.value,
            NodeRunStatus.STOPPED.value,
        }
        if any(node_run.status in attention_statuses for node_run in latest.values()):
            run.status = RunStatus.NEEDS_ATTENTION.value
            return run
        if latest and all(
            latest.get(node.node_id)
            and latest[node.node_id].status == NodeRunStatus.PASSED.value
            for node in spec.nodes
        ):
            run.status = RunStatus.COMPLETED.value
            return run
        if run.status != RunStatus.STOPPED.value:
            run.status = RunStatus.RUNNING.value
        return run

    def mark_driver_failed(self, run_id: str, reason: str) -> RunModel:
        run = self.get_run(run_id)
        if run.status in {
            RunStatus.COMPLETED.value,
            RunStatus.NEEDS_ATTENTION.value,
            RunStatus.STOPPED.value,
        }:
            return run

        latest = self.run_repo.list_latest_node_runs(run.id)
        for node_run in latest.values():
            if node_run.status in {
                NodeRunStatus.WAITING_EXECUTOR.value,
                NodeRunStatus.WAITING_VALIDATOR.value,
            }:
                node_run.status = NodeRunStatus.FAILED.value
                node_run.waiting_for_role = None
                node_run.stop_reason = reason

        run.status = RunStatus.NEEDS_ATTENTION.value
        run.stop_reason = reason
        return run

    def activate_ready_nodes(self, run_id: str) -> list[NodeRunModel]:
        run = self.get_run(run_id)
        spec = self.get_run_spec(run)
        workspace = self.get_workspace(run)
        latest = self.run_repo.list_latest_node_runs(run.id)
        created: list[NodeRunModel] = []
        for node in spec.nodes:
            if node.node_id in latest:
                continue
            if all(
                latest.get(dep) and latest[dep].status == NodeRunStatus.PASSED.value
                for dep in node.depends_on
            ):
                created.append(
                    self._create_node_round(
                        run,
                        spec,
                        node,
                        1,
                        workspace,
                        rework_brief=None,
                    )
                )
        self.refresh_run_status(run.id)
        return created

    def get_run_detail(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        spec = self.get_run_spec(run)
        node_runs = self.run_repo.list_node_runs(run.id)
        artifacts = self.artifact_service.list_run_artifacts(run.id)
        batch_id = self.run_repo.get_batch_id(run.id)
        return {
            "run": run,
            "workflow": {
                "workflow_id": spec.metadata.workflow_id,
                "version": spec.metadata.version,
                "title": spec.metadata.title,
            },
            "nodes": node_runs,
            "artifacts": artifacts,
            "batch_id": batch_id,
        }

    def list_run_summaries(self, workflow_id: str | None = None) -> list[dict[str, Any]]:
        runs = (
            self.run_repo.list_workflow_runs(workflow_id)
            if workflow_id is not None
            else self.run_repo.list_runs()
        )
        batch_map = self.run_repo.list_batch_ids([run.id for run in runs])
        items: list[dict[str, Any]] = []
        for run in runs:
            latest = self.run_repo.list_latest_node_runs(run.id)
            items.append(
                {
                    "run_id": run.id,
                    "workflow_id": run.workflow_id,
                    "version": run.workflow_version,
                    "status": run.status,
                    "stop_reason": run.stop_reason,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                    "batch_id": batch_map.get(run.id),
                    "attention_node_count": sum(
                        1
                        for node_run in latest.values()
                        if node_run.status
                        in {
                            NodeRunStatus.BLOCKED.value,
                            NodeRunStatus.FAILED.value,
                            NodeRunStatus.TIMED_OUT.value,
                            NodeRunStatus.REWORK_LIMIT.value,
                            NodeRunStatus.STOPPED.value,
                        }
                    ),
                }
            )
        return items

    def get_run_debug_overview(
        self,
        run_id: str,
        *,
        driver_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        detail = self.get_run_detail(run_id)
        run = detail["run"]
        workspace = self.get_workspace(run)
        timeline = [
            {
                "node_id": item.node_id,
                "round_no": item.round_no,
                "status": item.status,
                "waiting_for_role": item.waiting_for_role,
                "stop_reason": item.stop_reason,
                "rework_brief": item.rework_brief_json,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in detail["nodes"]
        ]
        latest = self.run_repo.list_latest_node_runs(run_id)
        call_map = {
            (item.node_id, item.round_no): self._read_round_claude_calls(workspace, item.node_id, item.round_no)
            for item in detail["nodes"]
        }
        current_focus = self._select_current_focus(latest, call_map)
        dispatchable = self._list_dispatchable_actions(run, latest)
        summary = self._build_overview_summary(latest)
        return {
            "run_id": run_id,
            "status": run.status,
            "stop_reason": run.stop_reason,
            "workflow": detail["workflow"],
            "timeline": timeline,
            "latest_nodes": [
                {
                    "node_id": item.node_id,
                    "round_no": item.round_no,
                    "status": item.status,
                    "waiting_for_role": item.waiting_for_role,
                    "stop_reason": item.stop_reason,
                }
                for item in latest.values()
            ],
            "driver": driver_state
            or {
                "run_id": run_id,
                "status": "idle",
                "mode": None,
                "max_steps": None,
                "started_at": None,
                "ended_at": None,
                "last_error": None,
                "stop_reason": None,
                "result_status": None,
            },
            "current_focus": current_focus,
            "summary": summary,
            "dispatchable": dispatchable,
            "activity": self._build_activity_stream(run, detail["nodes"], latest, call_map),
        }

    def _list_dispatchable_actions(
        self,
        run: RunModel,
        latest: dict[str, NodeRunModel],
    ) -> list[dict[str, Any]]:
        spec = self.get_run_spec(run)
        actions: list[dict[str, Any]] = []
        for node in spec.nodes:
            node_run = latest.get(node.node_id)
            if node_run is None:
                continue
            if node_run.status == NodeRunStatus.WAITING_EXECUTOR.value:
                actions.append(
                    {
                        "kind": "executor",
                        "node_id": node.node_id,
                        "round_no": node_run.round_no,
                    }
                )
                continue
            if node_run.status == NodeRunStatus.WAITING_VALIDATOR.value:
                for validator in node.validators:
                    existing = self.callback_repo.get_validator_round_event(
                        run.id,
                        node.node_id,
                        node_run.round_no,
                        validator.validator_id,
                    )
                    if existing is None:
                        actions.append(
                            {
                                "kind": "validator",
                                "node_id": node.node_id,
                                "round_no": node_run.round_no,
                                "validator_id": validator.validator_id,
                            }
                        )
        return actions

    def _build_overview_summary(
        self,
        latest: dict[str, NodeRunModel],
    ) -> dict[str, Any]:
        node_counts: dict[str, int] = {}
        attention_statuses = {
            NodeRunStatus.BLOCKED.value,
            NodeRunStatus.FAILED.value,
            NodeRunStatus.TIMED_OUT.value,
            NodeRunStatus.REWORK_LIMIT.value,
            NodeRunStatus.STOPPED.value,
        }
        attention_nodes: list[dict[str, Any]] = []
        for node_run in latest.values():
            node_counts[node_run.status] = node_counts.get(node_run.status, 0) + 1
            if node_run.status in attention_statuses:
                attention_nodes.append(
                    {
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "status": node_run.status,
                        "waiting_for_role": node_run.waiting_for_role,
                        "stop_reason": node_run.stop_reason,
                    }
                )
        return {
            "node_counts": node_counts,
            "attention_nodes": attention_nodes,
        }

    def retry_node(
        self,
        run_id: str,
        node_id: str,
        rework_brief: dict[str, Any] | None = None,
    ) -> NodeRunModel:
        run = self.get_run(run_id)
        spec = self.get_run_spec(run)
        node = next((item for item in spec.nodes if item.node_id == node_id), None)
        if node is None:
            raise NotFoundError(f"未找到节点: {node_id}")
        latest = self.run_repo.get_latest_node_run(run_id, node_id)
        if latest is None:
            raise NotFoundError(f"未找到 node run: {node_id}")
        if latest.status not in {
            NodeRunStatus.BLOCKED.value,
            NodeRunStatus.FAILED.value,
            NodeRunStatus.TIMED_OUT.value,
            NodeRunStatus.REWORK_LIMIT.value,
            NodeRunStatus.STOPPED.value,
        }:
            raise InvalidStateError(f"当前节点状态不允许重试: {latest.status}")
        latest.waiting_for_role = None
        workspace = self.get_workspace(run)
        retried = self._create_node_round(
            run,
            spec,
            node,
            latest.round_no + 1,
            workspace,
            rework_brief=rework_brief,
        )
        run.status = RunStatus.RUNNING.value
        run.stop_reason = None
        return retried

    def build_executor_context(
        self,
        run: RunModel,
        spec: WorkflowSpec,
        node: WorkflowNodeSpec,
        round_no: int,
        rework_brief: dict | None,
    ) -> dict:
        inputs: list[dict] = []
        for input_spec in node.inputs:
            source = input_spec.source
            if source.kind == "workflow_input":
                inputs.append(
                    {
                        "name": input_spec.name,
                        "source": {"kind": "workflow_input", "name": source.name},
                        "value": run.inputs_json.get(source.name),
                        "shape": input_spec.shape,
                        "required": input_spec.required,
                        "summary": input_spec.summary,
                    }
                )
                continue
            artifact = self.artifact_service.get_latest_node_artifact(
                run.id,
                source.node_id or "",
                source.output or "",
            )
            if artifact is None:
                raise InvalidStateError(
                    f"无法为节点 {node.node_id} 构建输入 {input_spec.name}，上游 artifact 缺失"
                )
            manifest = ArtifactManifest.model_validate(artifact.manifest_json)
            inputs.append(
                {
                    "name": input_spec.name,
                    "source": {
                        "kind": "node_output",
                        "node_id": source.node_id,
                        "output": source.output,
                    },
                    "artifact_ref": {
                        "artifact_id": manifest.artifact_id,
                        "version": manifest.version,
                    },
                    "manifest": manifest.model_dump(mode="json"),
                    "shape": input_spec.shape,
                    "required": input_spec.required,
                    "summary": input_spec.summary,
                }
            )
        return {
            "run_id": run.id,
            "workflow_id": spec.metadata.workflow_id,
            "workflow_version": spec.metadata.version,
            "node": node.model_dump(by_alias=True, mode="json"),
            "round_no": round_no,
            "inputs": inputs,
            "rework_brief": rework_brief,
        }

    def build_validator_context(
        self,
        run: RunModel,
        node: WorkflowNodeSpec,
        round_no: int,
        artifacts: list[ArtifactRef],
    ) -> dict:
        manifests = [
            self.artifact_service.resolve_ref(run.id, ref).model_dump(mode="json")
            for ref in artifacts
        ]
        return {
            "run_id": run.id,
            "node_id": node.node_id,
            "round_no": round_no,
            "acceptance": node.acceptance.model_dump(mode="json"),
            "gate": node.gate.model_dump(mode="json"),
            "artifacts": manifests,
        }

    def _activate_root_nodes(
        self,
        run: RunModel,
        spec: WorkflowSpec,
        workspace: RunWorkspace,
    ) -> None:
        roots = [node for node in spec.nodes if not node.depends_on]
        if not roots:
            raise ValidationError("workflow 没有可启动节点")
        for node in roots:
            self._create_node_round(run, spec, node, 1, workspace, rework_brief=None)

    def _create_node_round(
        self,
        run: RunModel,
        spec: WorkflowSpec,
        node: WorkflowNodeSpec,
        round_no: int,
        workspace: RunWorkspace,
        rework_brief: dict | None,
    ) -> NodeRunModel:
        node_run = self.run_repo.create_node_run(
            NodeRunModel(
                run_id=run.id,
                node_id=node.node_id,
                round_no=round_no,
                status=NodeRunStatus.WAITING_EXECUTOR.value,
                waiting_for_role="executor",
                rework_brief_json=rework_brief,
            )
        )
        context = self.build_executor_context(run, spec, node, round_no, rework_brief)
        self.workspace.write_executor_context(workspace, node.node_id, round_no, context)
        return node_run

    def _generate_run_id(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"run_{timestamp}_{uuid4().hex[:8]}"

    def _build_activity_stream(
        self,
        run: RunModel,
        node_runs: list[NodeRunModel],
        latest: dict[str, NodeRunModel],
        call_map: dict[tuple[str, int], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if run.created_at:
            events.append(
                {
                    "kind": "run_created",
                    "node_id": None,
                    "round_no": None,
                    "actor_role": None,
                    "validator_id": None,
                    "status": run.status,
                    "summary": "Run created",
                    "happened_at": run.created_at.isoformat(),
                    "call_id": None,
                }
            )

        for node_run in node_runs:
            key = (node_run.node_id, node_run.round_no)
            calls = call_map.get(key, {"executor_call_id": None, "validator_calls": []})
            created_at = node_run.created_at.isoformat() if node_run.created_at else None
            if created_at:
                events.append(
                    {
                        "kind": "node_round_created",
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "actor_role": "executor",
                        "validator_id": None,
                        "status": node_run.status,
                        "summary": f"{node_run.node_id} round {node_run.round_no} queued",
                        "happened_at": created_at,
                        "call_id": None,
                    }
                )

            executor_call_id = calls.get("executor_call_id")
            if executor_call_id:
                executor_meta = calls.get("executor_call")
                events.append(
                    {
                        "kind": "executor_started",
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "actor_role": "executor",
                        "validator_id": None,
                        "status": (executor_meta or {}).get("status", node_run.status),
                        "summary": f"Executor started for {node_run.node_id}",
                        "happened_at": (executor_meta or {}).get("started_at") or created_at,
                        "call_id": executor_call_id,
                    }
                )

            for validator_call in calls.get("validator_calls", []):
                validator_meta = validator_call.get("meta") or {}
                events.append(
                    {
                        "kind": "validator_started",
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "actor_role": "validator",
                        "validator_id": validator_call.get("validator_id"),
                        "status": validator_meta.get("status", node_run.status),
                        "summary": (
                            f"Validator {validator_call.get('validator_id')} started for {node_run.node_id}"
                        ),
                        "happened_at": validator_meta.get("started_at") or created_at,
                        "call_id": validator_call.get("call_id"),
                    }
                )

            if node_run.status in {
                NodeRunStatus.WAITING_EXECUTOR.value,
                NodeRunStatus.WAITING_VALIDATOR.value,
            }:
                updated_at = node_run.updated_at.isoformat() if node_run.updated_at else created_at
                events.append(
                    {
                        "kind": "node_waiting",
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "actor_role": node_run.waiting_for_role,
                        "validator_id": None,
                        "status": node_run.status,
                        "summary": f"{node_run.node_id} is waiting for {node_run.waiting_for_role or 'work'}",
                        "happened_at": updated_at,
                        "call_id": None,
                    }
                )

            if node_run.status not in {
                NodeRunStatus.WAITING_EXECUTOR.value,
                NodeRunStatus.WAITING_VALIDATOR.value,
            }:
                updated_at = node_run.updated_at.isoformat() if node_run.updated_at else created_at
                events.append(
                    {
                        "kind": "node_status_changed",
                        "node_id": node_run.node_id,
                        "round_no": node_run.round_no,
                        "actor_role": None,
                        "validator_id": None,
                        "status": node_run.status,
                        "summary": f"{node_run.node_id} changed to {node_run.status}",
                        "happened_at": updated_at,
                        "call_id": None,
                    }
                )

        for node_run in latest.values():
            callbacks = self._list_node_round_events(run.id, node_run.node_id, node_run.round_no)
            for callback in callbacks:
                status = callback.verdict_status or callback.execution_status
                events.append(
                    {
                        "kind": "callback_reported",
                        "node_id": callback.node_id,
                        "round_no": callback.round_no,
                        "actor_role": callback.actor_role,
                        "validator_id": callback.validator_id,
                        "status": status,
                        "summary": (
                            f"{callback.actor_role} callback reported"
                            + (f" ({callback.validator_id})" if callback.validator_id else "")
                        ),
                        "happened_at": callback.processed_at.isoformat() if callback.processed_at else None,
                        "call_id": None,
                    }
                )

        if run.updated_at and run.status in {
            RunStatus.COMPLETED.value,
            RunStatus.NEEDS_ATTENTION.value,
            RunStatus.STOPPED.value,
        }:
            events.append(
                {
                    "kind": "run_terminal",
                    "node_id": None,
                    "round_no": None,
                    "actor_role": None,
                    "validator_id": None,
                    "status": run.status,
                    "summary": f"Run reached {run.status}",
                    "happened_at": run.updated_at.isoformat(),
                    "call_id": None,
                }
            )

        events = [event for event in events if event["happened_at"]]
        events.sort(key=lambda item: item["happened_at"], reverse=True)
        return events

    def _select_current_focus(
        self,
        latest: dict[str, NodeRunModel],
        call_map: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, Any] | None:
        candidates = list(latest.values())
        if not candidates:
            return None

        def sort_key(node_run: NodeRunModel) -> tuple[int, float]:
            if node_run.status == NodeRunStatus.WAITING_EXECUTOR.value:
                priority = 0
            elif node_run.status == NodeRunStatus.WAITING_VALIDATOR.value:
                priority = 1
            elif node_run.status in {
                NodeRunStatus.REVISE.value,
                NodeRunStatus.BLOCKED.value,
                NodeRunStatus.FAILED.value,
                NodeRunStatus.TIMED_OUT.value,
                NodeRunStatus.REWORK_LIMIT.value,
            }:
                priority = 2
            else:
                priority = 3
            timestamp = node_run.updated_at or node_run.created_at or datetime.fromtimestamp(0, tz=timezone.utc)
            return (priority, -timestamp.timestamp())

        focus = sorted(candidates, key=sort_key)[0]
        calls = call_map.get((focus.node_id, focus.round_no), {"executor_call_id": None, "validator_calls": []})
        return {
            "node_id": focus.node_id,
            "round_no": focus.round_no,
            "status": focus.status,
            "waiting_for_role": focus.waiting_for_role,
            "stop_reason": focus.stop_reason,
            "executor_call_id": calls.get("executor_call_id"),
            "validator_calls": [
                {
                    "validator_id": item.get("validator_id"),
                    "call_id": item.get("call_id"),
                }
                for item in calls.get("validator_calls", [])
            ],
        }

    def _read_round_claude_calls(
        self,
        workspace: RunWorkspace,
        node_id: str,
        round_no: int,
    ) -> dict[str, Any]:
        round_dir = workspace.nodes_dir / node_id / "rounds" / str(round_no)
        if not round_dir.exists():
            return {"executor_call_id": None, "validator_calls": []}

        store = ClaudeCallStore(self.settings)
        executor_payload = self._read_call_payload(round_dir / "executor" / "claude_call.json")
        executor_call_id = executor_payload.get("call_id") if executor_payload else None
        executor_meta = self._load_call_meta(store, executor_call_id)

        validator_calls: list[dict[str, Any]] = []
        validators_dir = round_dir / "validators"
        if validators_dir.exists():
            for file_path in sorted(validators_dir.glob("*.claude_call.json")):
                payload = self._read_call_payload(file_path)
                if not payload:
                    continue
                call_id = payload.get("call_id")
                validator_calls.append(
                    {
                        "validator_id": payload.get("validator_id") or file_path.stem.split(".")[0],
                        "call_id": call_id,
                        "meta": self._load_call_meta(store, call_id),
                    }
                )

        return {
            "executor_call_id": executor_call_id,
            "executor_call": executor_meta,
            "validator_calls": validator_calls,
        }

    def _read_call_payload(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _load_call_meta(self, store: ClaudeCallStore, call_id: str | None) -> dict[str, Any] | None:
        if not call_id:
            return None
        try:
            return store.load_metadata(call_id)
        except NotFoundError:
            return None

    def _list_node_round_events(self, run_id: str, node_id: str, round_no: int) -> list[Any]:
        return self.callback_repo.list_node_round_events(run_id, node_id, round_no)
