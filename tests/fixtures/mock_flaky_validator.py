from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _next_attempt(task_file: Path) -> int:
    attempt_file = task_file.with_suffix(".attempt")
    current = 0
    if attempt_file.exists():
        current = int(attempt_file.read_text(encoding="utf-8"))
    current += 1
    attempt_file.write_text(str(current), encoding="utf-8")
    return current


def main() -> int:
    fail_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    task_file = os.getenv("PIPELINER_VALIDATOR_TASK_FILE")
    result_file = os.getenv("PIPELINER_VALIDATOR_RESULT_FILE")
    context_file = os.getenv("PIPELINER_VALIDATOR_CONTEXT_FILE")
    if not task_file or not result_file or not context_file:
        return 2

    task_path = Path(task_file)
    attempt = _next_attempt(task_path)
    if attempt <= fail_count:
        print(f"validator flaky failure {attempt}/{fail_count}", file=sys.stderr)
        return 1

    context = json.loads(Path(context_file).read_text(encoding="utf-8"))
    target_artifacts = [
        {"artifact_id": item["artifact_id"], "version": item["version"]}
        for item in context.get("artifacts", [])
        if item.get("artifact_id") and item.get("version")
    ]
    payload = {
        "execution": {"status": "completed"},
        "verdict": {
            "status": "pass",
            "summary": f"validated on attempt {attempt}",
            "target_artifacts": target_artifacts,
        },
    }
    Path(result_file).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
