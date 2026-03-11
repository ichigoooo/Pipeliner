from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeliner.config import Settings, get_settings


class ReportService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def save_authoring_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        reports_root = self.settings.data_dir / "reports"
        reports_root.mkdir(parents=True, exist_ok=True)
        report_path = reports_root / "authoring_reports.jsonl"
        record = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with report_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"stored": True, "path": str(report_path)}
