#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urlrequest


def _load_task_payload(task_path: Path) -> dict[str, Any]:
    return json.loads(task_path.read_text(encoding="utf-8"))


def _resolve_session_id(session_id: str | None, task_path: Path | None) -> str:
    if session_id:
        return session_id
    if task_path and task_path.exists():
        payload = _load_task_payload(task_path)
        value = payload.get("session_id")
        if isinstance(value, str) and value:
            return value
    raise ValueError("无法解析 session_id")


def _resolve_result_path(result_path: Path | None, task_path: Path | None) -> Path | None:
    if result_path:
        return result_path
    if task_path and task_path.exists():
        payload = _load_task_payload(task_path)
        value = payload.get("result_file")
        if isinstance(value, str) and value:
            return Path(value)
    env_path = os.getenv("PIPELINER_AUTHORING_RESULT_FILE")
    if env_path:
        return Path(env_path)
    return None


def _write_report_file(target: Path, payload: dict[str, Any], response: dict[str, Any]) -> None:
    content = {
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "response": response,
    }
    target.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suggestion", required=True)
    parser.add_argument("--explanation", required=True)
    parser.add_argument("--risk", required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--task-file")
    parser.add_argument("--result-file")
    parser.add_argument("--api-base-url")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    task_path = Path(args.task_file) if args.task_file else None
    if not task_path:
        env_task = os.getenv("PIPELINER_AUTHORING_TASK_FILE")
        task_path = Path(env_task) if env_task else None

    result_path = Path(args.result_file) if args.result_file else None
    resolved_result_path = _resolve_result_path(result_path, task_path)

    session_id = _resolve_session_id(args.session_id, task_path)

    base_url = (
        args.api_base_url
        or os.getenv("PIPELINER_API_BASE_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")
    endpoint = f"{base_url}/api/authoring/reports"

    payload = {
        "session_id": session_id,
        "suggestion": args.suggestion,
        "explanation": args.explanation,
        "risk": args.risk,
        "source": {"type": "authoring"},
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=args.timeout) as resp:
            resp_body = resp.read().decode("utf-8") if resp.readable() else ""
            response = {"status": resp.status, "body": resp_body}
    except Exception as exc:
        sys.stderr.write(f"report callback failed: {exc}\n")
        return 2

    if resolved_result_path:
        report_path = resolved_result_path.parent / "authoring_report.json"
        _write_report_file(report_path, payload, response)

    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
