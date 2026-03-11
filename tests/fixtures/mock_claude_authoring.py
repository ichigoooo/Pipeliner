from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    task_file = os.getenv("PIPELINER_AUTHORING_TASK_FILE")
    if not task_file and len(sys.argv) > 1:
        task_file = sys.argv[1]
    if not task_file:
        print("missing task file", file=sys.stderr)
        return 2

    payload = json.loads(Path(task_file).read_text(encoding="utf-8"))
    spec = payload.get("base_spec") or {}
    metadata = spec.get("metadata") or {}
    metadata["version"] = metadata.get("version", "v1.0.0") + "-gen"
    spec["metadata"] = metadata

    result_file = payload.get("result_file") or os.getenv("PIPELINER_AUTHORING_RESULT_FILE")
    output = json.dumps(spec, ensure_ascii=False, indent=2)
    if result_file:
        Path(result_file).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
