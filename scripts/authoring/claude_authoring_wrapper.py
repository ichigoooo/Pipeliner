#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import selectors
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from pipeliner.protocols.workflow import WorkflowSpec


def _parse_json_from_text(text: str) -> dict[str, Any]:
    content = text.strip()
    if not content:
        raise ValueError("authoring command returned empty output")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        sanitized = _sanitize_json_text(content)
        if sanitized != content:
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("authoring output is not valid JSON")
        snippet = content[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return json.loads(_sanitize_json_text(snippet))


def _load_result_payload(result_path: Path, stdout: str) -> dict[str, Any]:
    if result_path.exists():
        content = result_path.read_text(encoding="utf-8").strip()
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return json.loads(_sanitize_json_text(content))
    return _parse_json_from_text(stdout)


def _sanitize_json_text(text: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    length = len(text)
    index = 0
    while index < length:
        char = text[index]
        if not in_string:
            if char == '"':
                in_string = True
            result.append(char)
            index += 1
            continue
        if escaped:
            result.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            index += 1
            continue
        if char == '"':
            lookahead = index + 1
            while lookahead < length and text[lookahead] in " \t\r\n":
                lookahead += 1
            if lookahead < length and text[lookahead] not in ",:]}":
                result.append('\\"')
            else:
                in_string = False
                result.append(char)
            index += 1
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _truthy_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_claude_command(command: list[str]) -> bool:
    if not command:
        return False
    return Path(command[0]).name == "claude"


def _option_value(command: list[str], name: str) -> str | None:
    for index, arg in enumerate(command):
        if arg == name and index + 1 < len(command):
            return command[index + 1]
        if arg.startswith(f"{name}="):
            return arg.split("=", 1)[1]
    return None


def _has_flag(command: list[str], name: str) -> bool:
    return name in command or any(arg.startswith(f"{name}=") for arg in command)


def _ensure_flag(command: list[str], name: str, value: str | None = None) -> None:
    if _has_flag(command, name):
        return
    if value is None:
        command.append(name)
    else:
        command.extend([name, value])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    task_path = Path(args.task_file)
    result_path = Path(args.result_file)
    work_dir = Path(args.work_dir)

    inner_cmd = os.environ.get(
        "PIPELINER_CLAUDE_AUTHORING_INNER_CMD",
        "claude -p --permission-mode bypassPermissions",
    )
    command = shlex.split(inner_cmd)
    stream_enabled = _truthy_env("PIPELINER_CLAUDE_AUTHORING_STREAM", True)
    stream_json = False
    if stream_enabled and _is_claude_command(command):
        _ensure_flag(command, "-p")
        if _option_value(command, "--output-format") is None:
            _ensure_flag(command, "--output-format", "stream-json")
        output_format = _option_value(command, "--output-format")
        if output_format == "stream-json":
            _ensure_flag(command, "--include-partial-messages")
            _ensure_flag(command, "--verbose")
            stream_json = True

    prompt_text = prompt_path.read_text(encoding="utf-8")
    env = dict(os.environ)
    env["PIPELINER_AUTHORING_TASK_FILE"] = str(task_path)
    env["PIPELINER_AUTHORING_RESULT_FILE"] = str(result_path)

    process = subprocess.Popen(
        command,
        cwd=work_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if process.stdin:
        process.stdin.write(prompt_text.encode("utf-8"))
        process.stdin.flush()
        process.stdin.close()

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    stdout_line_buffer = bytearray()
    assistant_text_parts: list[str] = []
    saw_text_delta = False
    selector = selectors.DefaultSelector()
    assert process.stdout and process.stderr
    selector.register(process.stdout, selectors.EVENT_READ, data="stdout")
    selector.register(process.stderr, selectors.EVENT_READ, data="stderr")
    while selector.get_map():
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
                if not stream_json:
                    stdout_buffer.extend(chunk)
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                    continue
                stdout_line_buffer.extend(chunk)
                while b"\n" in stdout_line_buffer:
                    line, _, remainder = stdout_line_buffer.partition(b"\n")
                    stdout_line_buffer = bytearray(remainder)
                    line_text = line.decode("utf-8", errors="replace").strip()
                    if not line_text:
                        continue
                    try:
                        payload = json.loads(line_text)
                    except json.JSONDecodeError:
                        sys.stdout.write(line_text + "\n")
                        sys.stdout.flush()
                        continue
                    if payload.get("type") == "stream_event":
                        event = payload.get("event") or {}
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta") or {}
                            if delta.get("type") == "text_delta":
                                text = delta.get("text") or ""
                                if text:
                                    assistant_text_parts.append(text)
                                    sys.stdout.write(text)
                                    sys.stdout.flush()
                                    saw_text_delta = True
                            continue
                        continue
                    if payload.get("type") == "result" and not saw_text_delta:
                        result_text = payload.get("result")
                        if isinstance(result_text, str) and result_text:
                            assistant_text_parts.append(result_text)
                            sys.stdout.write(result_text)
                            sys.stdout.flush()
            else:
                stderr_buffer.extend(chunk)
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()

    returncode = process.wait()
    if stream_json:
        if stdout_line_buffer:
            trailing = stdout_line_buffer.decode("utf-8", errors="replace").strip()
            if trailing:
                try:
                    payload = json.loads(trailing)
                except json.JSONDecodeError:
                    sys.stdout.write(trailing)
                    sys.stdout.flush()
                else:
                    if payload.get("type") == "result" and not saw_text_delta:
                        result_text = payload.get("result")
                        if isinstance(result_text, str) and result_text:
                            assistant_text_parts.append(result_text)
                            sys.stdout.write(result_text)
                            sys.stdout.flush()
        stdout = "".join(assistant_text_parts)
    else:
        stdout = stdout_buffer.decode("utf-8", errors="replace")
    stderr = stderr_buffer.decode("utf-8", errors="replace")

    if returncode != 0:
        sys.stderr.write(stderr or f"authoring command failed(exit={returncode})\n")
        return returncode or 1

    try:
        payload = _load_result_payload(result_path, stdout)
        if not isinstance(payload, dict):
            raise ValueError("authoring result must be a JSON object")
        spec = WorkflowSpec.model_validate(payload)
        canonical = spec.model_dump(by_alias=True, mode="json")
    except Exception as exc:
        sys.stderr.write(f"authoring result invalid: {exc}\n")
        return 2

    require_report = os.getenv("PIPELINER_AUTHORING_REQUIRE_REPORT", "false").lower() == "true"
    report_path = work_dir / "authoring_report.json"
    if require_report and not report_path.exists():
        sys.stderr.write("authoring report callback missing: authoring_report.json\n")
        return 2

    result_path.write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")
    if not stream_json or not assistant_text_parts:
        sys.stdout.write(json.dumps(canonical, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
