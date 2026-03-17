from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExecutionTraceRecorder:
    def __init__(self, *paths: Path | None) -> None:
        self.paths = [path for path in paths if path is not None]

    def log(self, event: str, **fields: Any) -> None:
        if not self.paths:
            return
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
        for path in self.paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
