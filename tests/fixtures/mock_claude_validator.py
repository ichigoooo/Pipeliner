from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pass"
    prompt = sys.stdin.read()
    if "Pipeliner Claude Validator Task" not in prompt:
        print("missing expected prompt", file=sys.stderr)
        return 2

    task_file = os.getenv("PIPELINER_VALIDATOR_TASK_FILE")
    result_file = os.getenv("PIPELINER_VALIDATOR_RESULT_FILE")
    if not task_file or not result_file:
        print("missing validator env", file=sys.stderr)
        return 2

    task = json.loads(Path(task_file).read_text(encoding="utf-8"))
    result_path = Path(result_file)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "none":
        return 0

    payload: dict[str, object] = {"execution": {"status": "completed"}}
    if mode == "pass":
        payload["verdict"] = {
            "status": "pass",
            "summary": "validated",
            "target_artifacts": ["article_draft"],
        }
    elif mode == "revise":
        payload["verdict"] = {
            "status": "revise",
            "summary": "needs revision",
            "target_artifacts": [],
        }
        payload["rework_brief"] = {
            "must_fix": [
                {
                    "target": task["node_id"],
                    "problem": "content too weak",
                    "expected": "improve structure",
                }
            ],
            "preserve": ["topic"],
            "resubmit_instruction": "rewrite and resubmit",
            "evidence": ["validator mock"],
        }
    else:
        payload["verdict"] = {
            "status": "blocked",
            "summary": "blocked by mock",
            "target_artifacts": [],
        }

    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    marker = os.getenv("PIPELINER_TEST_CWD_FILE")
    if marker:
        Path(marker).write_text(os.getcwd(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
