from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    task_file = os.getenv("PIPELINER_VALIDATOR_TASK_FILE")
    result_file = os.getenv("PIPELINER_VALIDATOR_RESULT_FILE")
    context_file = os.getenv("PIPELINER_VALIDATOR_CONTEXT_FILE")
    if not task_file or not result_file or not context_file:
        return 2

    task = json.loads(Path(task_file).read_text(encoding="utf-8"))
    context = json.loads(Path(context_file).read_text(encoding="utf-8"))
    node_id = task["node_id"]
    round_no = task["round_no"]
    artifacts = context.get("artifacts", [])
    target_artifacts = [
        {"artifact_id": item["artifact_id"], "version": item["version"]}
        for item in artifacts
        if item.get("artifact_id") and item.get("version")
    ]

    payload: dict[str, object] = {"execution": {"status": "completed"}}
    if node_id == "draft_article" and round_no == 1:
        payload["verdict"] = {
            "status": "revise",
            "summary": "rewrite draft",
            "target_artifacts": target_artifacts,
        }
        payload["rework_brief"] = {
            "must_fix": [
                {
                    "target": "article_draft",
                    "problem": "draft too rough",
                    "expected": "make it publishable",
                }
            ],
            "preserve": ["topic"],
            "resubmit_instruction": "submit a stronger second draft",
            "evidence": ["sequence mock"],
        }
    else:
        payload["verdict"] = {
            "status": "pass",
            "summary": "approved",
            "target_artifacts": target_artifacts,
        }

    Path(result_file).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
