from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(slots=True)
class Settings:
    env: str = field(default_factory=lambda: os.getenv("PIPELINER_ENV", "development"))
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PIPELINER_DATA_DIR", ".pipeliner")).resolve()
    )
    default_timeout: str = field(
        default_factory=lambda: os.getenv("PIPELINER_DEFAULT_TIMEOUT", "2h")
    )
    authoring_timeout: str = field(
        default_factory=lambda: os.getenv("PIPELINER_AUTHORING_TIMEOUT", "20m")
    )
    default_max_rework_rounds: int = field(
        default_factory=lambda: int(os.getenv("PIPELINER_DEFAULT_MAX_REWORK_ROUNDS", "3"))
    )
    blocked_requires_manual: bool = field(
        default_factory=lambda: os.getenv("PIPELINER_BLOCKED_REQUIRES_MANUAL", "true").lower()
        == "true"
    )
    failure_requires_manual: bool = field(
        default_factory=lambda: os.getenv("PIPELINER_FAILURE_REQUIRES_MANUAL", "true").lower()
        == "true"
    )
    claude_executor_cmd: str = field(
        default_factory=lambda: os.getenv(
            "PIPELINER_CLAUDE_EXECUTOR_CMD",
            "claude -p --permission-mode bypassPermissions",
        )
    )
    claude_validator_cmd: str = field(
        default_factory=lambda: os.getenv(
            "PIPELINER_CLAUDE_VALIDATOR_CMD",
            "claude -p --permission-mode bypassPermissions",
        )
    )
    claude_authoring_cmd: str = field(
        default_factory=lambda: os.getenv(
            "PIPELINER_CLAUDE_AUTHORING_CMD",
            "claude -p --permission-mode bypassPermissions",
        )
    )
    claude_trace_enabled: bool = field(
        default_factory=lambda: os.getenv("PIPELINER_CLAUDE_TRACE_ENABLED", "true").lower()
        == "true"
    )
    claude_output_max_bytes: int = field(
        default_factory=lambda: int(os.getenv("PIPELINER_CLAUDE_OUTPUT_MAX_BYTES", "2000000"))
    )
    claude_output_retention: str = field(
        default_factory=lambda: os.getenv("PIPELINER_CLAUDE_OUTPUT_RETENTION", "7d")
    )
    projects_root: Path = field(
        default_factory=lambda: Path(os.getenv("PIPELINER_PROJECTS_ROOT", "projects")).resolve()
    )
    app_name: str = "Pipeliner"
    run_root: Path = field(init=False)
    database_path: Path = field(init=False)
    database_url: str = field(init=False)

    def __post_init__(self) -> None:
        self.run_root = self.data_dir / "runs"
        self.database_path = self.data_dir / "pipeliner.db"
        database_url = os.getenv("PIPELINER_DATABASE_URL")
        self.database_url = database_url or f"sqlite:///{self.database_path}"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.projects_root.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
