from __future__ import annotations

import json
import os
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import NodeRunModel, RunModel
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.protocols.artifact import ArtifactRef
from pipeliner.protocols.callback import (
    CallbackExecution,
    CallbackVerdict,
    NodeCallbackPayload,
    ReworkBrief,
)
from pipeliner.protocols.workflow import NodeValidatorSpec, WorkflowNodeSpec
from pipeliner.runtime import RuntimeCoordinator
from pipeliner.runtime.guards import parse_duration
from pipeliner.services.errors import ConflictError, InvalidStateError, NotFoundError
from pipeliner.services.project_initializer import ProjectInitializer
from pipeliner.services.run_service import RunService
from pipeliner.services.claude_call import ClaudeCallStore, run_streamed_command
from pipeliner.services.execution_trace import ExecutionTraceRecorder
from pipeliner.types import ExecutionStatus, NodeRunStatus, VerdictStatus


class ValidatorResultExecution(BaseModel):
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    message: str | None = None


class ValidatorResultVerdict(BaseModel):
    status: VerdictStatus
    summary: str | None = None
    target_artifacts: list[ArtifactRef] = Field(default_factory=list)


class ValidatorResultFile(BaseModel):
    execution: ValidatorResultExecution = Field(default_factory=ValidatorResultExecution)
    verdict: ValidatorResultVerdict | None = None
    rework_brief: ReworkBrief | None = None


class ClaudeValidatorDispatcher:
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
        self.project_initializer = ProjectInitializer(self.settings)

    def dispatch(
        self,
        run_id: str,
        node_id: str,
        validator_id: str,
        *,
        round_no: int | None = None,
        command_template: str | None = None,
    ) -> dict:
        run = self.run_service.get_run(run_id)
        spec = self.run_service.get_run_spec(run)
        node = self._get_node(spec.nodes, node_id)
        validator = self._get_validator(node, validator_id)
        node_run = self._select_node_run(run, node_id, round_no)

        if node_run.status != NodeRunStatus.WAITING_VALIDATOR.value:
            raise InvalidStateError(
                f"节点 {node_id} round {node_run.round_no} 当前不是 waiting_validator，无法调度"
            )
        existing = self.callback_repo.get_validator_round_event(
            run.id,
            node_id,
            node_run.round_no,
            validator_id,
        )
        if existing is not None:
            raise ConflictError(f"validator {validator_id} 在当前轮次已提交结果")

        workspace = self.run_service.get_workspace(run)
        dirs = self.run_service.workspace.ensure_node_round_dirs(
            workspace,
            node_id,
            node_run.round_no,
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
            / "validators"
            / validator.validator_id
        )
        trace_recorder = ExecutionTraceRecorder(
            dirs["validators_dir"] / f"{validator_id}.events.jsonl",
            mirror_dir / "execution_events.jsonl",
        )
        context_path = dirs["validators_dir"] / f"{validator_id}.json"
        if not context_path.exists():
            raise NotFoundError(f"validator context 文件不存在: {context_path}")

        result_path = dirs["validators_dir"] / f"{validator_id}.result.json"
        task_payload = {
            "run_id": run.id,
            "node_id": node.node_id,
            "round_no": node_run.round_no,
            "validator_id": validator.validator_id,
            "context_file": str(context_path),
            "result_file": str(result_path),
        }
        trace_recorder.log(
            "dispatch_prepared",
            run_id=run.id,
            node_id=node.node_id,
            round_no=node_run.round_no,
            validator_id=validator.validator_id,
            validator_skill=validator.skill,
            context_file=str(context_path),
            result_file=str(result_path),
        )
        task_path = dirs["validators_dir"] / f"{validator_id}.task.json"
        task_path.write_text(
            json.dumps(task_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        prompt_text = self._render_prompt(task_payload, validator)
        prompt_path = dirs["validators_dir"] / f"{validator_id}.prompt.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        stdout_path = dirs["validators_dir"] / f"{validator_id}.stdout.log"
        stderr_path = dirs["validators_dir"] / f"{validator_id}.stderr.log"
        command = self._build_command(
            command_template,
            prompt_path,
            task_path,
            result_path,
            dirs["validators_dir"],
        )
        call_store = ClaudeCallStore(self.settings)
        call_session = call_store.start_call(
            role="validator",
            context={
                "run_id": run.id,
                "node_id": node.node_id,
                "round_no": node_run.round_no,
                "validator_id": validator.validator_id,
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
            dirs["validators_dir"] / f"{validator_id}.claude_call.json",
            {"call_id": call_session.call_id, "validator_id": validator_id},
        )
        started_at = time.perf_counter()
        result = run_streamed_command(
            command=command,
            cwd=project_root,
            env=self._validator_env(task_path, context_path, result_path),
            input_text=prompt_text,
            output_session=call_session,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            mirror_stdout_path=mirror_dir / "stdout.log",
            mirror_stderr_path=mirror_dir / "stderr.log",
            trace_recorder=trace_recorder,
            first_byte_timeout=self._first_byte_timeout_seconds(spec),
        )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        error_message = None
        if result.first_byte_timed_out:
            error_message = "validator first byte timeout"
        elif result.timed_out:
            error_message = "validator command timeout"
        elif result.returncode != 0:
            error_message = f"validator command failed(exit={result.returncode})"
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
                "validator_failed",
                reason=f"validator command failed(exit={result.returncode})",
            )
            failure_message = error_message or f"validator command failed(exit={result.returncode})"
            payload = self._build_failure_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                validator_id=validator.validator_id,
                message=failure_message,
            )
            result = self.runtime.submit_callback(payload)
            response = self._failure_result(run, node, node_run, payload.event_id, result)
            response["claude_call_id"] = call_session.call_id
            return response

        if not result_path.exists():
            payload = self._build_failure_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                validator_id=validator.validator_id,
                message=f"validator 未生成结果文件: {result_path}",
            )
            result = self.runtime.submit_callback(payload)
            response = self._failure_result(run, node, node_run, payload.event_id, result)
            response["claude_call_id"] = call_session.call_id
            return response

        try:
            trace_recorder.log("validator_result_loading_started")
            result_payload = self._load_result_payload(result_path, context_path)
            callback_payload = self._build_result_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                validator_id=validator.validator_id,
                result_payload=result_payload,
            )
            trace_recorder.log(
                "validator_result_loaded",
                verdict_status=callback_payload.verdict.status.value if callback_payload.verdict else None,
            )
        except (PydanticValidationError, ValueError) as exc:
            trace_recorder.log("validator_result_invalid", error=str(exc))
            payload = self._build_failure_callback(
                run_id=run.id,
                node_id=node.node_id,
                round_no=node_run.round_no,
                validator_id=validator.validator_id,
                message=f"validator 结果文件无效: {exc}",
            )
            result = self.runtime.submit_callback(payload)
            response = self._failure_result(run, node, node_run, payload.event_id, result)
            response["claude_call_id"] = call_session.call_id
            return response

        trace_recorder.log("callback_submit_started", event_id=callback_payload.event_id)
        result = self.runtime.submit_callback(callback_payload)
        trace_recorder.log(
            "callback_submit_succeeded",
            event_id=callback_payload.event_id,
            run_status=result.get("run_status"),
        )
        return {
            "run_id": run.id,
            "node_id": node.node_id,
            "validator_id": validator.validator_id,
            "round_no": node_run.round_no,
            "status": (
                callback_payload.verdict.status.value
                if callback_payload.verdict
                else "completed"
            ),
            "event_id": callback_payload.event_id,
            "claude_call_id": call_session.call_id,
            "runtime": result,
        }

    def _first_byte_timeout_seconds(self, spec) -> float | None:
        try:
            return parse_duration(spec.runtime_guards_or_default().first_byte_timeout).total_seconds()
        except Exception:
            return None

    def _build_result_callback(
        self,
        *,
        run_id: str,
        node_id: str,
        round_no: int,
        validator_id: str,
        result_payload: ValidatorResultFile,
    ) -> NodeCallbackPayload:
        if (
            result_payload.execution.status == ExecutionStatus.COMPLETED
            and result_payload.verdict is None
        ):
            raise ValueError("validator completed 结果必须包含 verdict")
        verdict = None
        if result_payload.verdict is not None:
            verdict = CallbackVerdict(
                status=result_payload.verdict.status,
                summary=result_payload.verdict.summary,
                target_artifacts=result_payload.verdict.target_artifacts,
            )
        return NodeCallbackPayload(
            event_id=self._event_id("val"),
            sent_at=datetime.now(timezone.utc),
            run_id=run_id,
            node_id=node_id,
            round_no=round_no,
            actor={"role": "validator", "validator_id": validator_id},
            execution=CallbackExecution(
                status=result_payload.execution.status,
                message=result_payload.execution.message,
            ),
            verdict=verdict,
            rework_brief=result_payload.rework_brief,
        )

    def _build_failure_callback(
        self,
        *,
        run_id: str,
        node_id: str,
        round_no: int,
        validator_id: str,
        message: str,
    ) -> NodeCallbackPayload:
        return NodeCallbackPayload(
            event_id=self._event_id("val"),
            sent_at=datetime.now(timezone.utc),
            run_id=run_id,
            node_id=node_id,
            round_no=round_no,
            actor={"role": "validator", "validator_id": validator_id},
            execution=CallbackExecution(status=ExecutionStatus.FAILED, message=message),
            verdict={"status": "blocked", "summary": message, "target_artifacts": []},
        )

    def _build_command(
        self,
        command_template: str | None,
        prompt_path: Path,
        task_path: Path,
        result_path: Path,
        work_dir: Path,
    ) -> list[str]:
        template = command_template or self.settings.claude_validator_cmd
        formatted = template.format(
            prompt_file=str(prompt_path),
            task_file=str(task_path),
            result_file=str(result_path),
            work_dir=str(work_dir),
        )
        command = shlex.split(formatted)
        if "{prompt_file}" not in template and "{task_file}" not in template and len(command) == 1:
            command.append(str(prompt_path))
        return command

    def _validator_env(
        self,
        task_path: Path,
        context_path: Path,
        result_path: Path,
    ) -> dict[str, str]:
        env = dict(os.environ)
        env["PIPELINER_VALIDATOR_TASK_FILE"] = str(task_path)
        env["PIPELINER_VALIDATOR_CONTEXT_FILE"] = str(context_path)
        env["PIPELINER_VALIDATOR_RESULT_FILE"] = str(result_path)
        return env

    def _render_prompt(self, task_payload: dict, validator: NodeValidatorSpec) -> str:
        return (
            "# Pipeliner Claude Validator Task\n\n"
            "你是节点 validator。请读取上下文并生成判定结果。\n\n"
            f"- run_id: `{task_payload['run_id']}`\n"
            f"- node_id: `{task_payload['node_id']}`\n"
            f"- round_no: `{task_payload['round_no']}`\n"
            f"- validator_id: `{task_payload['validator_id']}`\n"
            f"- validator_skill: `{validator.skill}`\n"
            f"- context_file: `{task_payload['context_file']}`\n"
            f"- result_file: `{task_payload['result_file']}`\n\n"
            "必须写入 result_file，JSON 结构如下：\n"
            "1. pass:\n"
            '{"execution":{"status":"completed"},"verdict":{"status":"pass","summary":"...","target_artifacts":[]}}\n'
            "2. revise:\n"
            '{"execution":{"status":"completed"},"verdict":{"status":"revise","summary":"...","target_artifacts":[]},'
            '"rework_brief":{"must_fix":[{"target":"...","problem":"...","expected":"..."}],"preserve":[],"resubmit_instruction":"...","evidence":[]}}\n'
            "3. blocked:\n"
            '{"execution":{"status":"completed"},"verdict":{"status":"blocked","summary":"...","target_artifacts":[]}}\n'
            "约束：\n"
            "1. 不要改动任务目录之外的文件。\n"
            "2. 只写入 result_file，不要调用 runtime API。\n"
            "3. result_file 必须是合法 JSON。\n"
        )

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

    def _load_result_payload(self, result_path: Path, context_path: Path) -> ValidatorResultFile:
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        normalized = self._normalize_result_payload(raw, context_path)
        return ValidatorResultFile.model_validate(normalized)

    def _normalize_result_payload(self, payload: dict, context_path: Path) -> dict:
        verdict = payload.get("verdict")
        if not isinstance(verdict, dict):
            return payload
        target_artifacts = verdict.get("target_artifacts")
        if not isinstance(target_artifacts, list):
            return payload
        if not target_artifacts or all(isinstance(item, dict) for item in target_artifacts):
            return payload

        context = json.loads(context_path.read_text(encoding="utf-8"))
        artifact_lookup: dict[str, dict[str, str]] = {}
        for artifact in context.get("artifacts", []):
            if (
                not isinstance(artifact, dict)
                or not artifact.get("artifact_id")
                or not artifact.get("version")
            ):
                continue
            normalized_ref = {
                "artifact_id": artifact["artifact_id"],
                "version": artifact["version"],
            }
            artifact_lookup[artifact["artifact_id"]] = normalized_ref
            artifact_lookup[f"{artifact['artifact_id']}@{artifact['version']}"] = normalized_ref

        normalized_targets: list[dict] = []
        for item in target_artifacts:
            if isinstance(item, dict):
                normalized_targets.append(item)
                continue
            if isinstance(item, str) and item in artifact_lookup:
                normalized_targets.append(artifact_lookup[item])
                continue
            raise ValueError(f"无法解析 target_artifacts 项: {item}")
        verdict["target_artifacts"] = normalized_targets
        return payload

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

    def _event_id(self, prefix: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"evt_{prefix}_{timestamp}_{uuid4().hex[:8]}"

    def _get_node(self, nodes: list[WorkflowNodeSpec], node_id: str) -> WorkflowNodeSpec:
        for node in nodes:
            if node.node_id == node_id:
                return node
        raise NotFoundError(f"未找到节点: {node_id}")

    def _get_validator(self, node: WorkflowNodeSpec, validator_id: str) -> NodeValidatorSpec:
        for validator in node.validators:
            if validator.validator_id == validator_id:
                return validator
        raise NotFoundError(f"未找到 validator: {validator_id}")
