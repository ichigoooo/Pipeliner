from __future__ import annotations

import json
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
    if len(sys.argv) < 2:
        print("usage: mock_flaky_executor.py <task_file> [fail_count]", file=sys.stderr)
        return 2

    task_file = Path(sys.argv[1])
    fail_count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    payload = json.loads(task_file.read_text(encoding="utf-8"))
    attempt = _next_attempt(task_file)
    if attempt <= fail_count:
        print(f"executor flaky failure {attempt}/{fail_count}", file=sys.stderr)
        return 1

    for target in payload["targets"]:
        path = Path(target["absolute_path"])
        if target["kind"] == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# flaky output\n"
                f"attempt={attempt}\n"
                f"artifact={target['artifact_id']}@{target['version']}\n",
                encoding="utf-8",
            )
        else:
            path.mkdir(parents=True, exist_ok=True)
            (path / "index.txt").write_text(f"attempt={attempt}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
