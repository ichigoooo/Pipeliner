from __future__ import annotations

import json
import os
import shlex
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import NodeRunModel, RunModel
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.protocols.artifact import ArtifactManifest, ArtifactStorage, ProducedBy
from pipeliner.protocols.callback import (
    CallbackExecution,
    CallbackSubmission,
    NodeCallbackPayload,
)
from pipeliner.protocols.workflow import WorkflowNodeSpec
from pipeliner.runtime import RuntimeCoordinator
from pipeliner.runtime.guards import parse_duration
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.errors import InvalidStateError, NotFoundError, ValidationError
from pipeliner.services.project_initializer import ProjectInitializer
from pipeliner.services.run_service import RunService
from pipeliner.services.claude_call import ClaudeCallStore, run_streamed_command
from pipeliner.services.claude_env import (
    build_claude_env,
    detect_cli_network_error,
    is_claude_command,
    preflight_claude_host,
    resolve_claude_api_host,
)
from pipeliner.services.execution_trace import ExecutionTraceRecorder
from pipeliner.types import (
    ActorRole,
    ArtifactKind,
    ExecutionStatus,
    NodeRunStatus,
    StorageBackend,
)


@dataclass(slots=True)
class ArtifactTarget:
    artifact_id: str
    version: str
    shape: str
    kind: ArtifactKind
    relative_uri: str
    absolute_path: Path


class ClaudeExecutorDispatcher:
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
        self.runtime = RuntimeCoordinator(
            run_repo,
            workflow_repo,
            callback_repo,
            artifact_repo,
            self.settings,
        )
        self.artifact_service = ArtifactService(artifact_repo, run_repo, self.settings)
        self.project_initializer = ProjectInitializer(self.settings)

    def dispatch(
        self,
        run_id: str,
        node_id: str,
        *,
        round_no: int | None = None,
        command_template: str | None = None,
    ) -> dict:
        run = self.run_service.get_run(run_id)
        spec = self.run_service.get_run_spec(run)
        node = self._get_node(spec.nodes, node_id)
        node_run = self._select_node_run(run, node_id, round_no)

        if node_run.status != NodeRunStatus.WAITING_EXECUTOR.value:
            raise InvalidStateError(
                f"节点 {node_id} round {node_run.round_no} 当前不是 waiting_executor，无法调度"
            )

        workspace = self.run_service.get_workspace(run)
        dirs = self.run_service.workspace.ensure_node_round_dirs(
            workspace,
            node_id,
            node_run.round_no,
        )
        executor_dir = dirs["executor_dir"]
        self.project_initializer.ensure_node_skills(
            run.workflow_id,
            spec.model_dump(by_alias=True, mode="json"),
        )
        project_root = self.project_initializer.ensure_project_root(run.workflow_id)
        mirror_dir = (
            project_root
            / ".pipeliner"
            / "logs"
            / "runs"
            / run.id
            / node.node_id
            / "rounds"
            / str(node_run.round_no)
            / "executor"
        )
        trace_recorder = ExecutionTraceRecorder(
            executor_dir / "execution_events.jsonl",
            mirror_dir / "execution_events.jsonl",
        )
        context_path = executor_dir / "context.json"
        if not context_path.exists():
            raise NotFoundError(f"executor context 文件不存在: {context_path}")

        skill_name = node.executor.skill if node.executor else None
        skill_root = (
            project_root / ".claude" / "skills" / skill_name
            if isinstance(skill_name, str) and skill_name
            else None
        )
        skill_file = skill_root / "SKILL.md" if skill_root is not None else None
        skill_reference = skill_root / "references" / "node_context.json" if skill_root is not None else None

        targets = self._build_targets(run, node)
        for target in targets:
            if target.kind == ArtifactKind.FILE:
                target.absolute_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                target.absolute_path.mkdir(parents=True, exist_ok=True)

        task_payload = {
            "run_id": run.id,
            "node_id": node.node_id,
            "round_no": node_run.round_no,
            "context_file": str(context_path),
            "executor_skill": skill_name,
            "executor_skill_file": str(skill_file) if skill_file is not None else None,
            "executor_skill_reference": str(skill_reference) if skill_reference is not None else None,
            "targets": [
                {
                    "artifact_id": target.artifact_id,
                    "version": target.version,
                    "shape": target.shape,
                    "kind": target.kind.value,
                    "relative_uri": target.relative_uri,
                    "absolute_path": str(target.absolute_path),
                }
                for target in targets
            ],
        }
        trace_recorder.log(
            "dispatch_prepared",
            run_id=run.id,
            node_id=node.node_id,
            round_no=node_run.round_no,
            executor_skill=skill_name,
            context_file=str(context_path),
            executor_dir=str(executor_dir),
            targets=[target["absolute_path"] for target in task_payload["targets"]],
        )
        task_path = executor_dir / "executor_task.json"
        task_path.write_text(
            json.dumps(task_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        prompt_path = executor_dir / "claude_prompt.md"
        prompt_text = self._render_prompt(task_payload)
        prompt_path.write_text(prompt_text, encoding="utf-8")

        stdout_path = executor_dir / "executor_stdout.log"
        stderr_path = executor_dir / "executor_stderr.log"
        command = self._build_command(command_template, prompt_path, task_path, executor_dir)
        call_store = ClaudeCallStore(self.settings)
        call_session = call_store.start_call(
            role="executor",
            context={
                "run_id": run.id,
                "node_id": node.node_id,
                "round_no": node_run.round_no,
            },
            command=command,
            mirror_dir=mirror_dir,
        )
        trace_recorder.log(
            "claude_call_registered",
            call_id=call_session.call_id,
            command=" ".join(command),
        )
        self.run_service.workspace.write_json(
            executor_dir / "claude_call.json",
            {"call_id": call_session.call_id},
        )
        env = self._executor_env(task_path, context_path)
        if is_claude_command(command):
            env = build_claude_env(env, trace_recorder)
            host = resolve_claude_api_host(env)
            preflight_error = preflight_claude_host(host, trace_recorder)
            if preflight_error:
                call_session.mark_preflight_failure(
                    host=host,
                    error_message=preflight_error,
                )
                call_session.complete(
                    status="failed",
                    exit_code=-2,
                    error_message=preflight_error,
                    duration_ms=0,
                )
                trace_recorder.log(
                    "claude_call_completed",
                    call_id=call_session.call_id,
                    status="failed",
                    exit_code=-2,
                    error_message=preflight_error,
                    duration_ms=0,
                )
                payload = self._build_failure_callback(
                    run_id=run.id,
                    node_id=node.node_id,
                    round_no=node_run.round_no,
                    message=preflight_error,
                )
                result = self.runtime.submit_callback(payload)
                self.run_repo.session.commit()
                response = self._failure_result(run, node, node_run, payload.event_id, result)
                response["claude_call_id"] = call_session.call_id
                return response

        started_at = time.perf_counter()
        result = run_streamed_command(
            command=command,
            cwd=project_root,
            env=env,
            input_text=prompt_text,
            output_session=call_session,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            mirror_stdout_path=mirror_dir / "stdout.log",
            mirror_stderr_path=mirror_dir / "stderr.log",
            trace_recorder=trace_recorder,
            first_byte_timeout=self._first_byte_timeout_seconds(spec),
            timeout=self._timeout_seconds(spec),
        )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        error_message = None
        network_error = detect_cli_network_error(result.stdout, result.stderr)
        if result.timed_out:
            error_message = "executor command timeout"
        elif result.returncode != 0:
            error_message = network_error or f"executor command failed(exit={result.returncode})"
        call_session.complete(
            status="completed" if result.returncode == 0 else "failed",
            exit_code=result.returncode,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        trace_recorder.log(
            "claude_call_completed",
            call_id=call_session.call_id,
            status="completed" if result.returncode == 0 else "failed",
            exit_code=result.returncode,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        if result.returncode != 0:
            trace_recorder.log(
                "executor_failed",
                reason=error_message or f"executor command failed(exit={result.returncode})",
            )
            failure_message = error_message or f"executor command failed(exit={result.returncode})"
            payload = self._build_failure_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                message=failure_message,
            )
            result = self.runtime.submit_callback(payload)
            self.run_repo.session.commit()
            response = self._failure_result(run, node, node_run, payload.event_id, result)
            response["claude_call_id"] = call_session.call_id
            return response

        try:
            trace_recorder.log("artifact_publish_started")
            manifests = self._publish_manifests(run, node, node_run.round_no, targets)
            trace_recorder.log(
                "artifact_publish_succeeded",
                artifacts=[f"{manifest.artifact_id}@{manifest.version}" for manifest in manifests],
            )
        except ValidationError as exc:
            trace_recorder.log("artifact_publish_failed", error=str(exc))
            payload = self._build_failure_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                message=str(exc),
            )
            result = self.runtime.submit_callback(payload)
            self.run_repo.session.commit()
            response = self._failure_result(run, node, node_run, payload.event_id, result)
            response["claude_call_id"] = call_session.call_id
            return response
        callback_payload = self._build_success_callback(
            run.id,
            node.node_id,
            node_run.round_no,
            manifests,
        )
        trace_recorder.log("callback_submit_started", event_id=callback_payload.event_id)
        result = self.runtime.submit_callback(callback_payload)
        self.run_repo.session.commit()
        trace_recorder.log(
            "callback_submit_succeeded",
            event_id=callback_payload.event_id,
            run_status=result.get("run_status"),
        )
        return {
            "run_id": run.id,
            "node_id": node.node_id,
            "round_no": node_run.round_no,
            "status": "completed",
            "event_id": callback_payload.event_id,
            "claude_call_id": call_session.call_id,
            "artifacts": [
                {"artifact_id": manifest.artifact_id, "version": manifest.version}
                for manifest in manifests
            ],
            "runtime": result,
        }

    def _select_node_run(self, run: RunModel, node_id: str, round_no: int | None) -> NodeRunModel:
        if round_no is not None:
            node_run = self.run_repo.get_node_run(run.id, node_id, round_no)
            if node_run is None:
                raise NotFoundError(f"未找到节点轮次: {node_id} round {round_no}")
            return node_run

        node_run = self.run_repo.get_latest_node_run(run.id, node_id)
        if node_run is None:
            raise NotFoundError(f"节点 {node_id} 尚未初始化")
        return node_run

    def _failure_result(
        self,
        run: RunModel,
        node: WorkflowNodeSpec,
        node_run: NodeRunModel,
        event_id: str,
        runtime_result: dict,
    ) -> dict:
        return {
            "run_id": run.id,
            "node_id": node.node_id,
            "round_no": node_run.round_no,
            "status": "failed",
            "event_id": event_id,
            "runtime": runtime_result,
        }

    def _build_targets(self, run: RunModel, node: WorkflowNodeSpec) -> list[ArtifactTarget]:
        output_specs = {item.name: item for item in node.outputs}
        handoff = node.handoff.outputs or [item.name for item in node.outputs]
        targets: list[ArtifactTarget] = []
        for artifact_id in handoff:
            output_spec = output_specs.get(artifact_id)
            if output_spec is None:
                raise ValidationError(
                    f"节点 {node.node_id} handoff.outputs 引用了未知 output: {artifact_id}"
                )

            latest = self.artifact_service.get_latest_node_artifact(
                run.id,
                node.node_id,
                artifact_id,
            )
            version = self._next_version(latest.version if latest else None)
            kind = self._shape_to_kind(output_spec.shape)

            if kind == ArtifactKind.FILE:
                suffix = self._shape_to_suffix(output_spec.shape)
                relative_uri = (
                    f"{run.workspace_root}/artifacts/{artifact_id}@{version}/payload/{artifact_id}{suffix}"
                )
            else:
                relative_uri = f"{run.workspace_root}/artifacts/{artifact_id}@{version}/payload"

            targets.append(
                ArtifactTarget(
                    artifact_id=artifact_id,
                    version=version,
                    shape=output_spec.shape,
                    kind=kind,
                    relative_uri=relative_uri,
                    absolute_path=self.settings.data_dir / relative_uri,
                )
            )
        return targets

    def _publish_manifests(
        self,
        run: RunModel,
        node: WorkflowNodeSpec,
        round_no: int,
        targets: list[ArtifactTarget],
    ) -> list[ArtifactManifest]:
        manifests: list[ArtifactManifest] = []
        for target in targets:
            if target.kind == ArtifactKind.FILE and not target.absolute_path.exists():
                raise ValidationError(f"executor 未生成目标 artifact: {target.absolute_path}")
            if target.kind != ArtifactKind.FILE and not target.absolute_path.is_dir():
                raise ValidationError(f"executor 未生成目标 artifact 目录: {target.absolute_path}")

            digest, size = self.run_service.workspace.compute_digest(target.absolute_path)
            manifest = ArtifactManifest(
                artifact_id=target.artifact_id,
                version=target.version,
                kind=target.kind,
                produced_by=ProducedBy(
                    run_id=run.id,
                    node_id=node.node_id,
                    round_no=round_no,
                    role=ActorRole.EXECUTOR,
                ),
                storage=ArtifactStorage(backend=StorageBackend.LOCAL_FS, uri=target.relative_uri),
                integrity={"digest": digest, "size_bytes": size},
                created_at=datetime.now(timezone.utc),
            )
            self.artifact_service.publish_manifest(manifest)
            manifests.append(manifest)
        return manifests

    def _build_success_callback(
        self,
        run_id: str,
        node_id: str,
        round_no: int,
        manifests: list[ArtifactManifest],
    ) -> NodeCallbackPayload:
        return NodeCallbackPayload(
            event_id=self._event_id("exec"),
            sent_at=datetime.now(timezone.utc),
            run_id=run_id,
            node_id=node_id,
            round_no=round_no,
            actor={"role": "executor"},
            execution=CallbackExecution(status=ExecutionStatus.COMPLETED),
            submission=CallbackSubmission(
                artifacts=[
                    {"artifact_id": item.artifact_id, "version": item.version}
                    for item in manifests
                ]
            ),
        )

    def _build_failure_callback(
        self,
        *,
        run_id: str,
        node_id: str,
        round_no: int,
        message: str,
    ) -> NodeCallbackPayload:
        return NodeCallbackPayload(
            event_id=self._event_id("exec"),
            sent_at=datetime.now(timezone.utc),
            run_id=run_id,
            node_id=node_id,
            round_no=round_no,
            actor={"role": "executor"},
            execution=CallbackExecution(status=ExecutionStatus.FAILED, message=message),
            submission=CallbackSubmission(artifacts=[]),
        )

    def _build_command(
        self,
        command_template: str | None,
        prompt_path: Path,
        task_path: Path,
        executor_dir: Path,
    ) -> list[str]:
        template = command_template or self.settings.claude_executor_cmd
        formatted = template.format(
            prompt_file=str(prompt_path),
            task_file=str(task_path),
            work_dir=str(executor_dir),
        )
        command = shlex.split(formatted)
        if (
            "{prompt_file}" not in template
            and "{task_file}" not in template
            and len(command) == 1
        ):
            command.append(str(prompt_path))
        return command

    def _executor_env(self, task_path: Path, context_path: Path) -> dict[str, str]:
        env = dict(os.environ)
        env["PIPELINER_EXECUTOR_TASK_FILE"] = str(task_path)
        env["PIPELINER_EXECUTOR_CONTEXT_FILE"] = str(context_path)
        return env

    def _render_prompt(self, task_payload: dict) -> str:
        targets = "\n".join(
            (
                f"- artifact `{item['artifact_id']}@{item['version']}` "
                f"=> `{item['absolute_path']}` ({item['shape']})"
            )
            for item in task_payload["targets"]
        )
        skill_lines = ""
        if task_payload.get("executor_skill"):
            skill_lines = (
                f"- executor_skill: `{task_payload['executor_skill']}`\n"
                f"- skill_file: `{task_payload.get('executor_skill_file')}`\n"
                f"- skill_reference: `{task_payload.get('executor_skill_reference')}`\n\n"
                "执行要求：\n"
                "1. 先阅读 skill_file 和 skill_reference，再决定如何执行该节点。\n"
                "2. 产出逻辑应优先遵循 executor_skill 对应的工作方式，而不是泛化地自由发挥。\n\n"
            )
        return (
            "# Pipeliner Claude Executor Task\n\n"
            "你是节点 executor。请读取上下文并产出交付物。\n\n"
            f"- run_id: `{task_payload['run_id']}`\n"
            f"- node_id: `{task_payload['node_id']}`\n"
            f"- round_no: `{task_payload['round_no']}`\n"
            f"- context_file: `{task_payload['context_file']}`\n\n"
            f"{skill_lines}"
            "必须写入以下目标路径：\n"
            f"{targets}\n\n"
            "约束：\n"
            "1. 不要改动任务目录之外的文件。\n"
            "2. 只要产物写入成功即可退出，回调由 orchestrator 自动处理。\n"
        )

    def _next_version(self, current: str | None) -> str:
        if not current:
            return "v1"
        if not current.startswith("v"):
            return "v1"
        numeric = current[1:]
        if not numeric.isdigit():
            return "v1"
        return f"v{int(numeric) + 1}"

    def _first_byte_timeout_seconds(self, spec) -> float | None:
        try:
            return parse_duration(spec.runtime_guards_or_default().first_byte_timeout).total_seconds()
        except Exception:
            return None

    def _timeout_seconds(self, spec) -> float | None:
        try:
            return parse_duration(spec.runtime_guards_or_default().timeout).total_seconds()
        except Exception:
            return None

    def _shape_to_kind(self, shape: str) -> ArtifactKind:
        normalized = shape.lower()
        if normalized == "directory":
            return ArtifactKind.DIRECTORY
        if normalized == "collection":
            return ArtifactKind.COLLECTION
        return ArtifactKind.FILE

    def _shape_to_suffix(self, shape: str) -> str:
        normalized = shape.lower()
        if normalized == "json":
            return ".json"
        if normalized in {"file", "markdown", "md"}:
            return ".md"
        return ".txt"

    def _event_id(self, prefix: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"evt_{prefix}_{timestamp}_{uuid4().hex[:8]}"

    def _get_node(self, nodes: list[WorkflowNodeSpec], node_id: str) -> WorkflowNodeSpec:
        for node in nodes:
            if node.node_id == node_id:
                return node
        raise NotFoundError(f"未找到节点: {node_id}")
