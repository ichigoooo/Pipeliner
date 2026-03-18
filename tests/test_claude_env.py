from __future__ import annotations

import json
from pathlib import Path

from pipeliner.services import claude_env


def test_load_base_url_from_settings_env_block(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_BASE_URL": "https://api.kimi.com/coding/",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINER_CLAUDE_SETTINGS_PATH", str(settings_path))

    assert claude_env._load_base_url_from_settings() == "https://api.kimi.com/coding/"


def test_collect_claude_diagnostics_reads_settings_env_block(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_BASE_URL": "https://api.kimi.com/coding/",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINER_CLAUDE_SETTINGS_PATH", str(settings_path))
    monkeypatch.setattr(claude_env, "_cached_env", {})
    monkeypatch.setattr(claude_env, "_cached_at", 0.0)

    diagnostics = claude_env.collect_claude_diagnostics({})

    assert diagnostics["base_url"]["value"] == "https://api.kimi.com/coding/"
    assert diagnostics["base_url"]["source"] == "env"
    assert diagnostics["api_host"]["value"] == "api.kimi.com"
    assert diagnostics["sources"]["settings_loaded"] is True
