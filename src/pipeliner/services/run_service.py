from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import NodeRunModel, RunModel
from pipeliner.persistence.repositories import ArtifactRepository, RunRepository, WorkflowRepository
from pipeliner.protocols.artifact import ArtifactManifest, ArtifactRef
from pipeliner.protocols.workflow import WorkflowNodeSpec, WorkflowSpec
from pipeliner.services.artifact_service import ArtifactService
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

    def start_run(self, workflow_id: str, version: str, inputs: dict) -> RunModel:
        spec = self.workflow_service.load_spec_model(workflow_id, version)
        self._validate_required_inputs(spec, inputs)
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
        return {
            "run": run,
            "workflow": {
                "workflow_id": spec.metadata.workflow_id,
                "version": spec.metadata.version,
                "title": spec.metadata.title,
            },
            "nodes": node_runs,
            "artifacts": artifacts,
        }

    def list_run_summaries(self, workflow_id: str | None = None) -> list[dict[str, Any]]:
        runs = (
            self.run_repo.list_workflow_runs(workflow_id)
            if workflow_id is not None
            else self.run_repo.list_runs()
        )
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

    def get_run_debug_overview(self, run_id: str) -> dict[str, Any]:
        detail = self.get_run_detail(run_id)
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
        return {
            "run_id": run_id,
            "status": detail["run"].status,
            "stop_reason": detail["run"].stop_reason,
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

    def _validate_required_inputs(self, spec: WorkflowSpec, inputs: dict) -> None:
        missing = [item.name for item in spec.inputs if item.required and item.name not in inputs]
        if missing:
            raise ValidationError(f"缺少必填 workflow inputs: {', '.join(missing)}")

    def _generate_run_id(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"run_{timestamp}_{uuid4().hex[:8]}"
