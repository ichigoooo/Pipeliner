from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.runtime.guards import parse_duration


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
    ) -> AuthoringAgentResult:
        work_dir = self._ensure_work_dir(session_id)
        prompt_path = work_dir / "authoring_prompt.md"
        task_path = work_dir / "authoring_task.json"
        result_path = work_dir / "authoring_result.json"
        stdout_path = work_dir / "authoring_stdout.log"
        stderr_path = work_dir / "authoring_stderr.log"

        task_payload = {
            "session_id": session_id,
            "intent_brief": intent_brief,
            "instruction": instruction,
            "base_spec": base_spec,
            "result_file": str(result_path),
        }
        prompt_text = self._render_prompt(intent_brief, instruction, base_spec, result_path)

        task_path.write_text(
            json.dumps(task_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        prompt_path.write_text(prompt_text, encoding="utf-8")

        command = self._build_command(prompt_path, task_path, result_path, work_dir)
        started_at = time.perf_counter()
        exit_code: int | None = None
        stdout = ""
        stderr = ""
        timeout = self._timeout_seconds()
        try:
            process = subprocess.run(
                command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                input=prompt_text,
                env=self._authoring_env(task_path, result_path),
                timeout=timeout,
                check=False,
            )
            exit_code = process.returncode
            stdout = process.stdout or ""
            stderr = process.stderr or ""
        except FileNotFoundError as exc:
            exit_code = 127
            stderr = str(exc)
        except subprocess.TimeoutExpired as exc:
            exit_code = -1
            stdout = exc.stdout or ""
            stderr = exc.stderr or "authoring command timeout"
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        metadata = {
            "command": " ".join(command),
            "prompt_file": str(prompt_path),
            "task_file": str(task_path),
            "result_file": str(result_path),
            "stdout_file": str(stdout_path),
            "stderr_file": str(stderr_path),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        }

        if exit_code and exit_code != 0:
            raise AuthoringAgentError(
                f"authoring command failed(exit={exit_code})",
                metadata,
            )

        try:
            spec_payload = self._load_result_payload(result_path, stdout)
        except Exception as exc:
            raise AuthoringAgentError(f"authoring result invalid: {exc}", metadata) from exc
        if not isinstance(spec_payload, dict):
            raise AuthoringAgentError("authoring result must be a JSON object", metadata)

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
        command = shlex.split(formatted)
        if (
            "{prompt_file}" not in template
            and "{task_file}" not in template
            and len(command) == 1
        ):
            command.append(str(prompt_path))
        return command

    def _authoring_env(self, task_path: Path, result_path: Path) -> dict[str, str]:
        env = dict(os.environ)
        env["PIPELINER_AUTHORING_TASK_FILE"] = str(task_path)
        env["PIPELINER_AUTHORING_RESULT_FILE"] = str(result_path)
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
    ) -> str:
        spec_text = json.dumps(base_spec, ensure_ascii=False, indent=2)
        return (
            "# Pipeliner Authoring Task\n\n"
            "你是 workflow authoring agent。基于 intent brief 与 instruction 生成新的 workflow spec。\n\n"
            f"- intent brief: {intent_brief}\n"
            f"- instruction: {instruction}\n"
            f"- result file: {result_path}\n\n"
            "基础 spec（JSON）：\n"
            f"{spec_text}\n\n"
            "要求：\n"
            "1. 输出必须是完整的 JSON object，符合 pipeliner.workflow/v1alpha1。\n"
            "2. 不要输出 Markdown 或解释，只输出 JSON。\n"
            "3. 如果支持，请同时把结果写入 result file。\n"
        )
