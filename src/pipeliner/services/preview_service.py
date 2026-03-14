from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.repositories import ArtifactRepository, RunRepository
from pipeliner.protocols.artifact import ArtifactManifest
from pipeliner.services.errors import NotFoundError, ValidationError
from pipeliner.storage.local_fs import WorkspaceManager


class PreviewService:
    def __init__(
        self,
        run_repo: RunRepository,
        artifact_repo: ArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.artifact_repo = artifact_repo
        self.settings = settings or get_settings()
        self.workspace = WorkspaceManager(self.settings)
        self.max_preview_bytes = 200_000

    def preview_artifact(self, run_id: str, artifact_id: str, version: str) -> dict[str, Any]:
        run, artifact, storage_path = self._resolve_artifact_path(run_id, artifact_id, version)
        manifest = ArtifactManifest.model_validate(artifact.manifest_json)
        preview = self._preview_path(storage_path, manifest.model_dump(mode="json"))

        return {
            "artifact_id": artifact.artifact_id,
            "version": artifact.version,
            "kind": artifact.kind,
            "storage_uri": artifact.storage_uri,
            "manifest": manifest.model_dump(mode="json"),
            "preview": preview,
        }

    def open_artifact_folder(self, run_id: str, artifact_id: str, version: str) -> dict[str, Any]:
        _run, artifact, storage_path = self._resolve_artifact_path(run_id, artifact_id, version)
        target_path = storage_path if storage_path.is_dir() else storage_path.parent
        if not target_path.exists():
            raise NotFoundError(f"artifact 目录不存在: {target_path}")

        self._open_path(target_path)
        return {
            "artifact_id": artifact.artifact_id,
            "version": artifact.version,
            "target_path": str(storage_path),
            "opened_path": str(target_path),
        }

    def preview_log(self, run_id: str, relative_path: str) -> dict[str, Any]:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise NotFoundError(f"未找到 run: {run_id}")
        workspace = self.workspace.get_workspace(run.workflow_id, run.id)
        path = self._safe_join(workspace.root, relative_path)
        if not path.exists():
            raise NotFoundError(f"log 文件不存在: {relative_path}")
        return {
            "path": relative_path,
            "preview": self._preview_file(path),
        }

    def _resolve_storage_path(self, workflow_id: str, run_id: str, storage_uri: str) -> Path:
        base = self.settings.data_dir
        resolved = (base / storage_uri).resolve()
        workspace_root = (self.settings.run_root / workflow_id / run_id).resolve()
        if not self._is_within(resolved, base):
            raise ValidationError("artifact storage 路径非法")
        if not self._is_within(resolved, workspace_root):
            raise ValidationError("artifact 必须位于当前 run workspace 下")
        return resolved

    def _resolve_artifact_path(self, run_id: str, artifact_id: str, version: str) -> tuple[Any, Any, Path]:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise NotFoundError(f"未找到 run: {run_id}")
        artifact = self.artifact_repo.get_artifact(run_id, artifact_id, version)
        if artifact is None:
            raise NotFoundError(f"未找到 artifact: {artifact_id}@{version}")
        storage_path = self._resolve_storage_path(run.workflow_id, run.id, artifact.storage_uri)
        return run, artifact, storage_path

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

    def _safe_join(self, base: Path, relative_path: str) -> Path:
        if not relative_path or relative_path.startswith("/") or relative_path.startswith("\\"):
            raise ValidationError("路径必须为 workspace 内的相对路径")
        target = (base / relative_path).resolve()
        if not self._is_within(target, base.resolve()):
            raise ValidationError("非法路径访问")
        return target

    def _is_within(self, candidate: Path, base: Path) -> bool:
        try:
            candidate.relative_to(base)
        except ValueError:
            return False
        return True

    def _preview_path(self, path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        if path.is_dir():
            descriptor = manifest.get("descriptor") or {}
            entrypoint = descriptor.get("entrypoint") or descriptor.get("index_file")
            if entrypoint:
                entry_path = self._safe_join(path, entrypoint)
                if entry_path.exists() and entry_path.is_file():
                    preview = self._preview_file(entry_path)
                    preview["entrypoint"] = entrypoint
                    return preview
            return self._preview_directory(path)
        if path.is_file():
            return self._preview_file(path)
        raise NotFoundError(f"artifact payload 不存在: {path}")

    def _preview_directory(self, path: Path) -> dict[str, Any]:
        entries: list[str] = []
        for item in sorted(path.rglob("*")):
            if item.is_file():
                entries.append(item.relative_to(path).as_posix())
            if len(entries) >= 200:
                break
        return {
            "kind": "directory",
            "entries": entries,
            "truncated": len(entries) >= 200,
            "size_bytes": None,
            "limit_bytes": self.max_preview_bytes,
            "path": str(path),
        }

    def _preview_file(self, path: Path) -> dict[str, Any]:
        size = path.stat().st_size
        suffix = path.suffix.lower().lstrip(".")
        is_text = suffix in {"json", "txt", "md", "log", "yaml", "yml"}
        with path.open("rb") as handle:
            raw = handle.read(self.max_preview_bytes + 1)
        truncated = len(raw) > self.max_preview_bytes
        if truncated:
            raw = raw[: self.max_preview_bytes]
        if is_text:
            text = raw.decode("utf-8", errors="replace")
            if suffix == "json" and not truncated:
                try:
                    content = json.loads(text)
                    return {
                        "kind": "json",
                        "content": content,
                        "truncated": False,
                        "size_bytes": size,
                        "limit_bytes": self.max_preview_bytes,
                        "path": str(path),
                    }
                except json.JSONDecodeError:
                    pass
            return {
                "kind": "text",
                "content": text,
                "truncated": truncated,
                "size_bytes": size,
                "limit_bytes": self.max_preview_bytes,
                "path": str(path),
            }
        return {
            "kind": "binary",
            "content": None,
            "truncated": False,
            "size_bytes": size,
            "limit_bytes": self.max_preview_bytes,
            "path": str(path),
        }
