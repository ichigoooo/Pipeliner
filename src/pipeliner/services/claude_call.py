from __future__ import annotations

import json
import os
import re
import selectors
import subprocess
import time
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from pipeliner.config import Settings, get_settings
from pipeliner.runtime.guards import parse_duration
from pipeliner.services.errors import NotFoundError, ValidationError
from pipeliner.services.execution_trace import ExecutionTraceRecorder


@dataclass(slots=True)
class StreamedProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    first_byte_timed_out: bool


@dataclass(slots=True)
class ClaudeCallSession:
    call_id: str
    log_path: Path
    meta_path: Path
    max_bytes: int
    started_at: datetime
    _handle: BinaryIO
    _mirror_handle: BinaryIO | None = None
    mirror_log_path: Path | None = None
    mirror_meta_path: Path | None = None
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
        if self._mirror_handle is not None:
            self._mirror_handle.write(chunk)
            self._mirror_handle.flush()
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
        if self._mirror_handle is not None:
            self._mirror_handle.flush()
            self._mirror_handle.close()
        payload = _read_metadata(self.meta_path)
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
        _write_metadata(self.meta_path, payload)
        if self.mirror_meta_path is not None:
            _write_metadata(self.mirror_meta_path, payload)

    def attach_process(self, pid: int) -> None:
        payload = _read_metadata(self.meta_path)
        payload["pid"] = pid
        _write_metadata(self.meta_path, payload)
        if self.mirror_meta_path is not None:
            _write_metadata(self.mirror_meta_path, payload)

    def mark_slow_start(
        self,
        *,
        elapsed_ms: int,
        message: str,
    ) -> None:
        payload = _read_metadata(self.meta_path)
        if payload.get("slow_start_detected"):
            return
        payload.update(
            {
                "slow_start_detected": True,
                "slow_start_at": datetime.now(timezone.utc).isoformat(),
                "slow_start_after_ms": elapsed_ms,
                "slow_start_message": message,
            }
        )
        _write_metadata(self.meta_path, payload)
        if self.mirror_meta_path is not None:
            _write_metadata(self.mirror_meta_path, payload)

    def mark_preflight_failure(
        self,
        *,
        host: str,
        error_message: str,
    ) -> None:
        payload = _read_metadata(self.meta_path)
        payload.update(
            {
                "preflight_failed": True,
                "preflight_host": host,
                "preflight_error": error_message,
                "preflight_failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_metadata(self.meta_path, payload)
        if self.mirror_meta_path is not None:
            _write_metadata(self.mirror_meta_path, payload)


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
        mirror_dir: Path | None = None,
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
            "pid": None,
            "slow_start_detected": False,
            "slow_start_at": None,
            "slow_start_after_ms": None,
            "slow_start_message": None,
            "preflight_failed": False,
            "preflight_host": None,
            "preflight_error": None,
            "preflight_failed_at": None,
        }
        _write_metadata(meta_path, payload)
        handle = log_path.open("ab")
        mirror_handle = None
        mirror_log_path = None
        mirror_meta_path = None
        if mirror_dir is not None:
            mirror_dir.mkdir(parents=True, exist_ok=True)
            mirror_log_path = mirror_dir / "claude_call.log"
            mirror_meta_path = mirror_dir / "claude_call.json"
            _write_metadata(mirror_meta_path, payload)
            mirror_handle = mirror_log_path.open("ab")
        return ClaudeCallSession(
            call_id=call_id,
            log_path=log_path,
            meta_path=meta_path,
            max_bytes=self.max_bytes,
            started_at=started_at,
            _handle=handle,
            _mirror_handle=mirror_handle,
            mirror_log_path=mirror_log_path,
            mirror_meta_path=mirror_meta_path,
        )

    def load_metadata(self, call_id: str) -> dict[str, Any]:
        meta_path = self._meta_path(call_id)
        if not meta_path.exists():
            raise NotFoundError(f"未找到 Claude 调用记录: {call_id}")
        payload = _read_metadata(meta_path)
        if payload.get("status") == "running":
            payload = self._reconcile_running_metadata(call_id, payload)
        return payload

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

    def _reconcile_running_metadata(self, call_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        pid = payload.get("pid")
        if isinstance(pid, int) and pid > 0:
            if self._process_exists(pid):
                return payload
            return self._mark_failed_metadata(
                call_id,
                payload,
                error_message="claude process exited unexpectedly",
            )
        if self._is_running_call_stale(payload):
            return self._mark_failed_metadata(
                call_id,
                payload,
                error_message="claude call metadata became stale before completion",
            )
        return payload

    def _mark_failed_metadata(
        self,
        call_id: str,
        payload: dict[str, Any],
        *,
        error_message: str,
    ) -> dict[str, Any]:
        payload.update(
            {
                "status": "failed",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": payload.get("exit_code") if payload.get("exit_code") is not None else -2,
                "error_message": payload.get("error_message") or error_message,
            }
        )
        _write_metadata(self._meta_path(call_id), payload)
        return payload

    def _is_running_call_stale(self, payload: dict[str, Any]) -> bool:
        started_at = payload.get("started_at")
        if not isinstance(started_at, str) or not started_at:
            return False
        try:
            started = datetime.fromisoformat(started_at)
        except ValueError:
            return False
        timeout = self._role_timeout(payload.get("role"))
        if timeout is None:
            return False
        return datetime.now(timezone.utc) - started > timeout

    def _role_timeout(self, role: Any):
        raw = self.settings.authoring_timeout if role == "authoring" else self.settings.default_timeout
        try:
            return parse_duration(raw)
        except Exception:
            return None

    def _process_exists(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

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
    mirror_stdout_path: Path | None = None,
    mirror_stderr_path: Path | None = None,
    trace_recorder: ExecutionTraceRecorder | None = None,
    first_byte_timeout: float | None = None,
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
        if trace_recorder is not None:
            trace_recorder.log("process_spawn_failed", error=str(exc), command=command, cwd=str(cwd))
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_bytes(b"")
        stderr_path.write_bytes(message)
        if mirror_stdout_path is not None:
            mirror_stdout_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_stdout_path.write_bytes(b"")
        if mirror_stderr_path is not None:
            mirror_stderr_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_stderr_path.write_bytes(message)
        return StreamedProcessResult(
            returncode=127,
            stdout="",
            stderr=str(exc),
            timed_out=False,
            first_byte_timed_out=False,
        )

    output_session.attach_process(process.pid)
    if trace_recorder is not None:
        trace_recorder.log(
            "process_started",
            pid=process.pid,
            command=command,
            cwd=str(cwd),
            timeout_seconds=timeout,
        )
    if process.stdin:
        if input_text:
            process.stdin.write(input_text.encode("utf-8"))
            process.stdin.flush()
        process.stdin.close()

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        stdout_file = stack.enter_context(stdout_path.open("wb"))
        stderr_file = stack.enter_context(stderr_path.open("wb"))
        mirror_stdout_file = None
        mirror_stderr_file = None
        if mirror_stdout_path is not None:
            mirror_stdout_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_stdout_file = stack.enter_context(mirror_stdout_path.open("wb"))
        if mirror_stderr_path is not None:
            mirror_stderr_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_stderr_file = stack.enter_context(mirror_stderr_path.open("wb"))
        selector = selectors.DefaultSelector()
        assert process.stdout and process.stderr
        selector.register(process.stdout, selectors.EVENT_READ, data="stdout")
        selector.register(process.stderr, selectors.EVENT_READ, data="stderr")
        timed_out = False
        first_byte_timed_out = False
        first_output_logged = False
        first_byte_warning_logged = False
        last_heartbeat = time.perf_counter()
        while selector.get_map():
            elapsed = time.perf_counter() - started
            if (
                first_byte_timeout is not None
                and not first_output_logged
                and not first_byte_warning_logged
                and output_session.bytes_written == 0
                and elapsed > first_byte_timeout
            ):
                first_byte_timed_out = True
                first_byte_warning_logged = True
                output_session.mark_slow_start(
                    elapsed_ms=int(elapsed * 1000),
                    message="Claude 已启动，但首字节等待时间已超过阈值，仍可继续等待。",
                )
                if trace_recorder is not None:
                    trace_recorder.log(
                        "first_byte_timeout_reached",
                        elapsed_seconds=round(elapsed, 3),
                        pid=process.pid,
                        bytes_written=output_session.bytes_written,
                    )
            if timeout is not None and not timed_out:
                if elapsed >= timeout:
                    process.kill()
                    timed_out = True
                    if trace_recorder is not None:
                        trace_recorder.log(
                            "timeout_reached",
                            elapsed_seconds=round(elapsed, 3),
                            pid=process.pid,
                            bytes_written=output_session.bytes_written,
                        )
            events = selector.select(timeout=0.2)
            if trace_recorder is not None and time.perf_counter() - last_heartbeat >= 10:
                trace_recorder.log(
                    "heartbeat",
                    elapsed_seconds=round(time.perf_counter() - started, 3),
                    pid=process.pid,
                    bytes_written=output_session.bytes_written,
                    process_alive=process.poll() is None,
                )
                last_heartbeat = time.perf_counter()
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
                    if mirror_stdout_file is not None:
                        mirror_stdout_file.write(chunk)
                else:
                    stderr_buffer.extend(chunk)
                    stderr_file.write(chunk)
                    if mirror_stderr_file is not None:
                        mirror_stderr_file.write(chunk)
                output_session.append(chunk)
                if trace_recorder is not None and not first_output_logged:
                    trace_recorder.log(
                        "first_output",
                        stream=key.data,
                        bytes_written=output_session.bytes_written,
                        preview=chunk[:200].decode("utf-8", errors="replace"),
                    )
                    first_output_logged = True

    returncode = process.wait()
    if timeout is not None and timed_out:
        returncode = -1
    if trace_recorder is not None:
        trace_recorder.log(
            "process_exited",
            pid=process.pid,
            returncode=returncode,
            timed_out=timed_out,
            first_byte_timed_out=first_byte_timed_out,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            bytes_written=output_session.bytes_written,
        )
    stdout_text = stdout_buffer.decode("utf-8", errors="replace")
    stderr_text = stderr_buffer.decode("utf-8", errors="replace")
    return StreamedProcessResult(
        returncode=returncode,
        stdout=stdout_text,
        stderr=stderr_text,
        timed_out=timed_out,
        first_byte_timed_out=first_byte_timed_out,
    )


def _read_metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)
