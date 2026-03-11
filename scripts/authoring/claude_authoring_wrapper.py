#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("authoring output is not valid JSON")
        return json.loads(content[start : end + 1])


def _load_result_payload(result_path: Path, stdout: str) -> dict[str, Any]:
    if result_path.exists():
        content = result_path.read_text(encoding="utf-8").strip()
        if content:
            return json.loads(content)
    return _parse_json_from_text(stdout)


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

    prompt_text = prompt_path.read_text(encoding="utf-8")
    env = dict(os.environ)
    env["PIPELINER_AUTHORING_TASK_FILE"] = str(task_path)
    env["PIPELINER_AUTHORING_RESULT_FILE"] = str(result_path)

    process = subprocess.run(
        command,
        cwd=work_dir,
        input=prompt_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    stdout = process.stdout or ""
    stderr = process.stderr or ""

    if process.returncode != 0:
        sys.stderr.write(stderr or f"authoring command failed(exit={process.returncode})\n")
        return process.returncode or 1

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
    sys.stdout.write(json.dumps(canonical, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
