from __future__ import annotations

import json
import re
import selectors
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.runtime.guards import parse_duration
from pipeliner.services.errors import NotFoundError, ValidationError


@dataclass(slots=True)
class StreamedProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


@dataclass(slots=True)
class ClaudeCallSession:
    call_id: str
    log_path: Path
    meta_path: Path
    max_bytes: int
    started_at: datetime
    _handle: BinaryIO
    bytes_written: int = 0
    truncated: bool = False

    def append(self, chunk: bytes) -> None:
        if not chunk or self.truncated:
            return
        remaining = self.max_bytes - self.bytes_written
        if remaining <= 0:
            self.truncated = True
            return
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
            self.truncated = True
        self._handle.write(chunk)
        self._handle.flush()
        self.bytes_written += len(chunk)

    def complete(
        self,
        *,
        status: str,
        exit_code: int | None,
        error_message: str | None,
        duration_ms: int | None,
    ) -> None:
        self._handle.flush()
        self._handle.close()
        payload = json.loads(self.meta_path.read_text(encoding="utf-8"))
        payload.update(
            {
                "status": status,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": exit_code,
                "error_message": error_message,
                "bytes_written": self.bytes_written,
                "truncated": self.truncated,
                "duration_ms": duration_ms,
            }
        )
        self.meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ClaudeCallStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_dir = self.settings.data_dir / "claude_calls"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = self.settings.claude_output_max_bytes
        self.retention = self._parse_retention(self.settings.claude_output_retention)

    def start_call(
        self,
        *,
        role: str,
        context: dict[str, Any],
        command: list[str] | None,
        call_id: str | None = None,
    ) -> ClaudeCallSession:
        self.cleanup()
        if call_id:
            self._validate_call_id(call_id)
            log_path = self.base_dir / f"{call_id}.log"
            meta_path = self.base_dir / f"{call_id}.json"
            if log_path.exists() or meta_path.exists():
                raise ValidationError("call_id 已存在")
        else:
            call_id = self._build_call_id(role)
            log_path = self.base_dir / f"{call_id}.log"
            meta_path = self.base_dir / f"{call_id}.json"
        started_at = datetime.now(timezone.utc)
        payload = {
            "call_id": call_id,
            "role": role,
            "status": "running",
            "started_at": started_at.isoformat(),
            "ended_at": None,
            "exit_code": None,
            "error_message": None,
            "bytes_written": 0,
            "truncated": False,
            "limit_bytes": self.max_bytes,
            "output_path": str(log_path.relative_to(self.settings.data_dir)),
            "command": " ".join(command) if command else None,
            "context": context,
        }
        meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        handle = log_path.open("ab")
        return ClaudeCallSession(
            call_id=call_id,
            log_path=log_path,
            meta_path=meta_path,
            max_bytes=self.max_bytes,
            started_at=started_at,
            _handle=handle,
        )

    def load_metadata(self, call_id: str) -> dict[str, Any]:
        meta_path = self._meta_path(call_id)
        if not meta_path.exists():
            raise NotFoundError(f"未找到 Claude 调用记录: {call_id}")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def read_chunk(self, call_id: str, offset: int, limit: int) -> bytes:
        if offset < 0:
            raise ValidationError("offset 必须为非负整数")
        if limit <= 0 or limit > 2_000_000:
            raise ValidationError("limit 超出允许范围")
        log_path = self._log_path(call_id)
        if not log_path.exists():
            raise NotFoundError(f"未找到 Claude 输出日志: {call_id}")
        with log_path.open("rb") as handle:
            handle.seek(offset)
            return handle.read(limit)

    def cleanup(self) -> None:
        if self.retention is None:
            return
        cutoff = datetime.now(timezone.utc) - self.retention
        for meta_path in self.base_dir.glob("*.json"):
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            ended_at = payload.get("ended_at")
            status = payload.get("status")
            if status == "running" or not ended_at:
                continue
            try:
                ended = datetime.fromisoformat(ended_at)
            except ValueError:
                continue
            if ended > cutoff:
                continue
            call_id = payload.get("call_id") or meta_path.stem
            log_path = self._log_path(call_id)
            if log_path.exists():
                log_path.unlink()
            meta_path.unlink()

    def _parse_retention(self, raw: str | None):
        if not raw:
            return None
        try:
            return parse_duration(raw)
        except Exception:
            return None

    def _build_call_id(self, role: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = uuid4().hex[:8]
        return f"claude_{role}_{timestamp}_{suffix}"

    def _meta_path(self, call_id: str) -> Path:
        self._validate_call_id(call_id)
        return self.base_dir / f"{call_id}.json"

    def _log_path(self, call_id: str) -> Path:
        self._validate_call_id(call_id)
        return self.base_dir / f"{call_id}.log"

    def _validate_call_id(self, call_id: str) -> None:
        if not call_id or not re.fullmatch(r"[a-zA-Z0-9_-]+", call_id):
            raise ValidationError("call_id 格式非法")


def run_streamed_command(
    *,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    input_text: str | None,
    output_session: ClaudeCallSession,
    stdout_path: Path,
    stderr_path: Path,
    timeout: float | None = None,
) -> StreamedProcessResult:
    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        message = str(exc).encode("utf-8", errors="replace")
        output_session.append(message)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_bytes(b"")
        stderr_path.write_bytes(message)
        return StreamedProcessResult(returncode=127, stdout="", stderr=str(exc), timed_out=False)

    if process.stdin:
        if input_text:
            process.stdin.write(input_text.encode("utf-8"))
            process.stdin.flush()
        process.stdin.close()

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        selector = selectors.DefaultSelector()
        assert process.stdout and process.stderr
        selector.register(process.stdout, selectors.EVENT_READ, data="stdout")
        selector.register(process.stderr, selectors.EVENT_READ, data="stderr")
        timed_out = False
        while selector.get_map():
            if timeout is not None and not timed_out:
                elapsed = time.perf_counter() - started
                if elapsed > timeout:
                    process.kill()
                    timed_out = True
            events = selector.select(timeout=0.2)
            if not events:
                if process.poll() is not None and not selector.get_map():
                    break
            for key, _ in events:
                stream = key.fileobj
                chunk = stream.read1(4096) if hasattr(stream, "read1") else stream.read(4096)
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                if key.data == "stdout":
                    stdout_buffer.extend(chunk)
                    stdout_file.write(chunk)
                else:
                    stderr_buffer.extend(chunk)
                    stderr_file.write(chunk)
                output_session.append(chunk)

    returncode = process.wait()
    if timeout is not None and timed_out:
        returncode = -1
    stdout_text = stdout_buffer.decode("utf-8", errors="replace")
    stderr_text = stderr_buffer.decode("utf-8", errors="replace")
    return StreamedProcessResult(
        returncode=returncode,
        stdout=stdout_text,
        stderr=stderr_text,
        timed_out=timed_out,
    )
