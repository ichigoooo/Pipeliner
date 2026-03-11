from __future__ import annotations

import os
from typing import Any, Callable

from pipeliner.config import Settings
from pipeliner.persistence.repositories import WorkflowRepository


class SettingsService:
    def __init__(self, settings: Settings, workflow_repo: WorkflowRepository) -> None:
        self.settings = settings
        self.workflow_repo = workflow_repo

    def build_snapshot(self) -> dict[str, Any]:
        workflows = self.workflow_repo.list_definitions()
        observed_skills: dict[str, dict[str, Any]] = {}
        for definition in workflows:
            for version in definition.versions:
                for node in version.spec_json.get("nodes", []):
                    executor_skill = node.get("executor", {}).get("skill")
                    if executor_skill:
                        observed_skills.setdefault(
                            executor_skill,
                            {
                                "skill": executor_skill,
                                "used_by": [],
                            },
                        )["used_by"].append(
                            f"{definition.workflow_id}@{version.version}:{node.get('node_id')}"
                        )
                    for validator in node.get("validators", []):
                        skill = validator.get("skill")
                        if skill:
                            observed_skills.setdefault(
                                skill,
                                {
                                    "skill": skill,
                                    "used_by": [],
                                },
                            )["used_by"].append(
                                f"{definition.workflow_id}@{version.version}:{node.get('node_id')}/{validator.get('validator_id')}"
                            )

        return {
            "executor_command": self._env_value(
                "PIPELINER_CLAUDE_EXECUTOR_CMD",
                self.settings.claude_executor_cmd,
                "claude -p --permission-mode bypassPermissions",
            ),
            "validator_command": self._env_value(
                "PIPELINER_CLAUDE_VALIDATOR_CMD",
                self.settings.claude_validator_cmd,
                "claude -p --permission-mode bypassPermissions",
            ),
            "authoring_command": self._env_value(
                "PIPELINER_CLAUDE_AUTHORING_CMD",
                self.settings.claude_authoring_cmd,
                "claude -p --permission-mode bypassPermissions",
            ),
            "storage": {
                "backend": {
                    "value": "local_fs",
                    "source": "code_default",
                },
                "data_dir": self._env_value(
                    "PIPELINER_DATA_DIR",
                    str(self.settings.data_dir),
                    ".pipeliner",
                ),
                "run_root": {
                    "value": str(self.settings.run_root),
                    "source": "derived_from_data_dir",
                },
            },
            "database": {
                "url": self._env_value(
                    "PIPELINER_DATABASE_URL",
                    self.settings.database_url,
                    f"sqlite:///{self.settings.database_path}",
                    redact=lambda value: value if value.startswith("sqlite:///") else "***REDACTED***",
                ),
                "path": {
                    "value": str(self.settings.database_path),
                    "source": "derived_from_data_dir",
                },
            },
            "runtime_guards": {
                "default_timeout": self._env_value(
                    "PIPELINER_DEFAULT_TIMEOUT",
                    self.settings.default_timeout,
                    "30m",
                ),
                "authoring_timeout": self._env_value(
                    "PIPELINER_AUTHORING_TIMEOUT",
                    self.settings.authoring_timeout,
                    "20m",
                ),
                "default_max_rework_rounds": self._env_value(
                    "PIPELINER_DEFAULT_MAX_REWORK_ROUNDS",
                    self.settings.default_max_rework_rounds,
                    3,
                ),
                "blocked_requires_manual": self._env_value(
                    "PIPELINER_BLOCKED_REQUIRES_MANUAL",
                    self.settings.blocked_requires_manual,
                    True,
                ),
                "failure_requires_manual": self._env_value(
                    "PIPELINER_FAILURE_REQUIRES_MANUAL",
                    self.settings.failure_requires_manual,
                    True,
                ),
            },
            "providers": [
                {
                    "provider": "claude",
                    "role": "executor",
                    "command_template": self._env_value(
                        "PIPELINER_CLAUDE_EXECUTOR_CMD",
                        self.settings.claude_executor_cmd,
                        "claude -p --permission-mode bypassPermissions",
                    ),
                },
                {
                    "provider": "claude",
                    "role": "validator",
                    "command_template": self._env_value(
                        "PIPELINER_CLAUDE_VALIDATOR_CMD",
                        self.settings.claude_validator_cmd,
                        "claude -p --permission-mode bypassPermissions",
                    ),
                },
                {
                    "provider": "claude",
                    "role": "authoring",
                    "command_template": self._env_value(
                        "PIPELINER_CLAUDE_AUTHORING_CMD",
                        self.settings.claude_authoring_cmd,
                        "claude -p --permission-mode bypassPermissions",
                    ),
                },
            ],
            "skills": sorted(observed_skills.values(), key=lambda item: item["skill"]),
        }

    def _env_value(
        self,
        env_key: str,
        current_value: Any,
        default_value: Any,
        redact: Callable[[Any], Any] | None = None,
    ) -> dict[str, Any]:
        source = "env" if env_key in os.environ else "default"
        value = current_value
        if redact is not None:
            value = redact(value)
        return {
            "value": value,
            "source": source,
            "env_key": env_key,
            "default": default_value,
        }
