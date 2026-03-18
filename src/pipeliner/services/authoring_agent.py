from __future__ import annotations

import json
import os
import shlex
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.runtime.guards import parse_duration
from pipeliner.services.claude_call import ClaudeCallStore, run_streamed_command
from pipeliner.services.claude_env import (
    build_claude_env,
    detect_cli_network_error,
    is_claude_command,
    preflight_claude_host,
    resolve_claude_api_host,
)
from pipeliner.services.execution_trace import ExecutionTraceRecorder


@dataclass(slots=True)
class AuthoringAgentResult:
    spec_json: dict[str, Any]
    metadata: dict[str, Any]


class AuthoringAgentError(RuntimeError):
    def __init__(self, message: str, metadata: dict[str, Any]) -> None:
        super().__init__(message)
        self.metadata = metadata


class AuthoringAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(
        self,
        *,
        session_id: str,
        intent_brief: str,
        instruction: str,
        base_spec: dict[str, Any],
        project_dir: Path | None = None,
        claude_call_id: str | None = None,
    ) -> AuthoringAgentResult:
        work_dir = self._ensure_work_dir(session_id)
        prompt_path = work_dir / "authoring_prompt.md"
        task_path = work_dir / "authoring_task.json"
        result_path = work_dir / "authoring_result.json"
        stdout_path = work_dir / "authoring_stdout.log"
        stderr_path = work_dir / "authoring_stderr.log"
        mirror_dir = (
            project_dir / ".pipeliner" / "logs" / "authoring" / session_id / (claude_call_id or "latest")
            if project_dir
            else None
        )
        trace_recorder = ExecutionTraceRecorder(
            work_dir / "execution_events.jsonl",
            mirror_dir / "execution_events.jsonl" if mirror_dir else None,
        )

        task_payload = {
            "session_id": session_id,
            "intent_brief": intent_brief,
            "instruction": instruction,
            "base_spec": base_spec,
            "result_file": str(result_path),
        }
        trace_recorder.log(
            "dispatch_prepared",
            session_id=session_id,
            project_dir=str(project_dir) if project_dir else None,
            prompt_file=str(prompt_path),
            task_file=str(task_path),
            result_file=str(result_path),
        )
        prompt_text = self._render_prompt(
            intent_brief,
            instruction,
            base_spec,
            result_path,
            project_dir,
        )

        task_path.write_text(
            json.dumps(task_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        prompt_path.write_text(prompt_text, encoding="utf-8")

        command = self._build_command(prompt_path, task_path, result_path, work_dir)
        call_store = ClaudeCallStore(self.settings)
        call_session = call_store.start_call(
            role="authoring",
            context={
                "session_id": session_id,
                "work_dir": str(work_dir),
                "project_dir": str(project_dir) if project_dir else None,
            },
            command=command,
            call_id=claude_call_id,
            mirror_dir=mirror_dir,
        )
        trace_recorder.log(
            "claude_call_registered",
            call_id=call_session.call_id,
            command=" ".join(command),
        )
        env = self._authoring_env(task_path, result_path, project_dir)
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
                metadata = {
                    "command": " ".join(command),
                    "prompt_file": str(prompt_path),
                    "task_file": str(task_path),
                    "result_file": str(result_path),
                    "stdout_file": str(stdout_path),
                    "stderr_file": str(stderr_path),
                    "exit_code": -2,
                    "duration_ms": 0,
                    "claude_call_id": call_session.call_id,
                    "preflight_failed": True,
                    "preflight_host": host,
                    "preflight_error": preflight_error,
                }
                trace_recorder.log("authoring_failed", reason=preflight_error)
                raise AuthoringAgentError(preflight_error, metadata)

        started_at = time.perf_counter()
        timeout = self._timeout_seconds()
        result = run_streamed_command(
            command=command,
            cwd=project_dir or work_dir,
            env=env,
            input_text=prompt_text,
            output_session=call_session,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            mirror_stdout_path=mirror_dir / "stdout.log" if mirror_dir else None,
            mirror_stderr_path=mirror_dir / "stderr.log" if mirror_dir else None,
            trace_recorder=trace_recorder,
            timeout=timeout,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        metadata = {
            "command": " ".join(command),
            "prompt_file": str(prompt_path),
            "task_file": str(task_path),
            "result_file": str(result_path),
            "stdout_file": str(stdout_path),
            "stderr_file": str(stderr_path),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "claude_call_id": call_session.call_id,
        }
        error_message = None
        network_error = detect_cli_network_error(stdout, stderr)
        if result.timed_out:
            error_message = "authoring command timeout"
        elif exit_code and exit_code != 0:
            error_message = network_error or f"authoring command failed(exit={exit_code})"
        call_session.complete(
            status="completed" if exit_code == 0 else "failed",
            exit_code=exit_code,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        trace_recorder.log(
            "claude_call_completed",
            call_id=call_session.call_id,
            status="completed" if exit_code == 0 else "failed",
            exit_code=exit_code,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        if exit_code and exit_code != 0:
            trace_recorder.log("authoring_failed", reason=error_message or f"authoring command failed(exit={exit_code})")
            raise AuthoringAgentError(
                error_message or f"authoring command failed(exit={exit_code})",
                metadata,
            )

        try:
            trace_recorder.log("result_loading_started")
            spec_payload = self._load_result_payload(result_path, stdout)
        except Exception as exc:
            trace_recorder.log("result_loading_failed", error=str(exc))
            raise AuthoringAgentError(f"authoring result invalid: {exc}", metadata) from exc
        if not isinstance(spec_payload, dict):
            trace_recorder.log("result_loading_failed", error="authoring result must be a JSON object")
            raise AuthoringAgentError("authoring result must be a JSON object", metadata)

        trace_recorder.log("result_loaded")

        return AuthoringAgentResult(spec_json=spec_payload, metadata=metadata)

    def _ensure_work_dir(self, session_id: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        root = self.settings.data_dir / "authoring" / session_id / "generations"
        path = root / f"{timestamp}_{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _timeout_seconds(self) -> float | None:
        try:
            return parse_duration(self.settings.authoring_timeout).total_seconds()
        except Exception:
            return None

    def _build_command(
        self,
        prompt_path: Path,
        task_path: Path,
        result_path: Path,
        work_dir: Path,
    ) -> list[str]:
        template = self.settings.claude_authoring_cmd
        formatted = template.format(
            prompt_file=str(prompt_path),
            task_file=str(task_path),
            result_file=str(result_path),
            work_dir=str(work_dir),
        )
        command = [self._resolve_repo_relative_path(part) for part in shlex.split(formatted)]
        if (
            "{prompt_file}" not in template
            and "{task_file}" not in template
            and len(command) == 1
        ):
            command.append(str(prompt_path))
        return command

    def _resolve_repo_relative_path(self, part: str) -> str:
        if not part or part.startswith("-"):
            return part
        candidate = Path(part)
        if candidate.is_absolute():
            return part
        if "/" not in part and not part.endswith(".py") and not part.startswith("."):
            return part
        repo_root = Path(__file__).resolve().parents[3]
        repo_candidate = repo_root / part
        if repo_candidate.exists():
            return str(repo_candidate)
        return part

    def _authoring_env(
        self,
        task_path: Path,
        result_path: Path,
        project_dir: Path | None,
    ) -> dict[str, str]:
        env = dict(os.environ)
        env["PIPELINER_AUTHORING_TASK_FILE"] = str(task_path)
        env["PIPELINER_AUTHORING_RESULT_FILE"] = str(result_path)
        if project_dir:
            env["PIPELINER_PROJECT_DIR"] = str(project_dir)
        return env

    def _load_result_payload(self, result_path: Path, stdout: str) -> dict[str, Any]:
        if result_path.exists():
            content = result_path.read_text(encoding="utf-8").strip()
            if content:
                return json.loads(content)
        return self._parse_json_from_text(stdout)

    def _parse_json_from_text(self, text: str) -> dict[str, Any]:
        content = text.strip()
        if not content:
            raise ValueError("authoring command returned empty output")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("authoring output is not valid JSON")
            return json.loads(content[start : end + 1])

    def _render_prompt(
        self,
        intent_brief: str,
        instruction: str,
        base_spec: dict[str, Any],
        result_path: Path,
        project_dir: Path | None,
    ) -> str:
        spec_text = json.dumps(base_spec, ensure_ascii=False, indent=2)
        project_hint = (
            f"项目目录：{project_dir}\n" if project_dir else "项目目录：未指定（使用当前工作目录）\n"
        )
        return (
            "# Pipeliner Authoring Task\n\n"
            "你是 workflow authoring agent。基于 intent brief 与 instruction 生成新的 workflow spec。\n\n"
            f"- intent brief: {intent_brief}\n"
            f"- instruction: {instruction}\n"
            f"- result file: {result_path}\n\n"
            f"{project_hint}\n"
            "技能使用指引：\n"
            "- 创建或更新 workflow spec：使用 workflow-authoring skill。\n"
            "- 基于 attention/rework 进行迭代：使用 workflow-iteration skill。\n"
            "- 校验/审阅 spec：使用 workflow-review skill。\n\n"
            "节点技能约束：\n"
            "- 每个节点必须绑定 executor.skill 与 validators[].skill。\n"
            "- skill 名称为 kebab-case，且在 workflow 内唯一。\n"
            "- 新增节点或 validator 时，为其绑定新的 skill 名称并保持与 .claude/skills 一致。\n\n"
            "提交约束：\n"
            "- 最终提交必须写入 result file，并可被校验脚本验证通过。\n"
            "- 如果无法通过脚本校验，停止输出并说明原因。\n\n"
            "回调要求：\n"
            "- 生成完成后必须运行脚本执行回调：\n"
            "  python scripts/authoring/report_callback.py "
            "--suggestion \"...\" --explanation \"...\" --risk \"...\"\n"
            "- suggestion/explanation/risk 必须与本次工作结果相关。\n\n"
            "基础 spec（JSON）：\n"
            f"{spec_text}\n\n"
            "要求：\n"
            "1. 输出必须是完整的 JSON object，符合 pipeliner.workflow/v1alpha1。\n"
            "2. 不要输出 Markdown 或解释，只输出 JSON。\n"
            "3. inputs / outputs / nodes / validators 必须是对象数组。\n"
            "4. 每个 node 输出必须包含 name / shape / summary。\n"
            "5. 每个 node 必须包含 acceptance {done_means, pass_condition}。\n"
            "6. 如果支持，请同时把结果写入 result file。\n"
        )
