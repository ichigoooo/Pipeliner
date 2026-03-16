from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.services.errors import ValidationError
from pipeliner.services.project_initializer import ProjectInitializer


class ProjectService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.project_initializer = ProjectInitializer(self.settings)

    def open_project_root(self, workflow_id: str) -> dict[str, Any]:
        project_root = self.project_initializer.ensure_project_root(workflow_id)
        self._open_path(project_root)
        return {
            "workflow_id": workflow_id,
            "opened_path": str(project_root),
        }

    def _open_path(self, path: Path) -> None:
        if sys.platform == "darwin":
            command = ["open", str(path)]
        elif sys.platform.startswith("linux"):
            command = ["xdg-open", str(path)]
        elif sys.platform.startswith("win"):
            command = ["explorer", str(path)]
        else:
            raise ValidationError("当前环境不支持打开文件夹")

        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ValidationError("当前环境缺少打开文件夹所需命令") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip() or "打开文件夹失败"
            raise ValidationError(detail) from exc
        except OSError as exc:
            raise ValidationError(str(exc)) from exc
