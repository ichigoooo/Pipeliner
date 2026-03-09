from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: mock_claude_executor.py <task_file>", file=sys.stderr)
        return 2

    task_file = Path(sys.argv[1])
    payload = json.loads(task_file.read_text(encoding="utf-8"))
    for target in payload["targets"]:
        path = Path(target["absolute_path"])
        kind = target["kind"]
        if kind == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                path.write_text(
                    json.dumps(
                        {
                            "run_id": payload["run_id"],
                            "node_id": payload["node_id"],
                            "round_no": payload["round_no"],
                            "artifact_id": target["artifact_id"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            else:
                path.write_text(
                    f"# mock output\nrun={payload['run_id']}\nnode={payload['node_id']}\n"
                    f"artifact={target['artifact_id']}@{target['version']}\n",
                    encoding="utf-8",
                )
        else:
            path.mkdir(parents=True, exist_ok=True)
            (path / "index.txt").write_text("mock directory output\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
