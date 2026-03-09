from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeliner.config import Settings


@dataclass(slots=True)
class RunWorkspace:
    workflow_id: str
    run_id: str
    root: Path
    relative_root: str
    inputs_dir: Path
    nodes_dir: Path
    artifacts_dir: Path
    callbacks_dir: Path


class WorkspaceManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_directories()

    def create_run_workspace(self, workflow_id: str, run_id: str) -> RunWorkspace:
        root = self.settings.run_root / workflow_id / run_id
        inputs_dir = root / "inputs"
        nodes_dir = root / "nodes"
        artifacts_dir = root / "artifacts"
        callbacks_dir = root / "callbacks"
        for path in (inputs_dir, nodes_dir, artifacts_dir, callbacks_dir):
            path.mkdir(parents=True, exist_ok=True)
        relative_root = Path("runs") / workflow_id / run_id
        return RunWorkspace(
            workflow_id=workflow_id,
            run_id=run_id,
            root=root,
            relative_root=relative_root.as_posix(),
            inputs_dir=inputs_dir,
            nodes_dir=nodes_dir,
            artifacts_dir=artifacts_dir,
            callbacks_dir=callbacks_dir,
        )

    def get_workspace(self, workflow_id: str, run_id: str) -> RunWorkspace:
        root = self.settings.run_root / workflow_id / run_id
        return RunWorkspace(
            workflow_id=workflow_id,
            run_id=run_id,
            root=root,
            relative_root=(Path("runs") / workflow_id / run_id).as_posix(),
            inputs_dir=root / "inputs",
            nodes_dir=root / "nodes",
            artifacts_dir=root / "artifacts",
            callbacks_dir=root / "callbacks",
        )

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_workflow_inputs(self, workspace: RunWorkspace, inputs: dict[str, Any]) -> Path:
        path = workspace.inputs_dir / "workflow_inputs.json"
        self.write_json(path, inputs)
        return path

    def ensure_node_round_dirs(
        self,
        workspace: RunWorkspace,
        node_id: str,
        round_no: int,
    ) -> dict[str, Path]:
        round_dir = workspace.nodes_dir / node_id / "rounds" / str(round_no)
        executor_dir = round_dir / "executor"
        validators_dir = round_dir / "validators"
        for path in (round_dir, executor_dir, validators_dir):
            path.mkdir(parents=True, exist_ok=True)
        return {
            "round_dir": round_dir,
            "executor_dir": executor_dir,
            "validators_dir": validators_dir,
        }

    def write_executor_context(
        self,
        workspace: RunWorkspace,
        node_id: str,
        round_no: int,
        payload: dict[str, Any],
    ) -> Path:
        dirs = self.ensure_node_round_dirs(workspace, node_id, round_no)
        path = dirs["executor_dir"] / "context.json"
        self.write_json(path, payload)
        return path

    def write_validator_context(
        self,
        workspace: RunWorkspace,
        node_id: str,
        round_no: int,
        validator_id: str,
        payload: dict[str, Any],
    ) -> Path:
        dirs = self.ensure_node_round_dirs(workspace, node_id, round_no)
        path = dirs["validators_dir"] / f"{validator_id}.json"
        self.write_json(path, payload)
        return path

    def write_callback_archive(
        self,
        workspace: RunWorkspace,
        event_id: str,
        payload: dict[str, Any],
    ) -> Path:
        path = workspace.callbacks_dir / f"{event_id}.json"
        self.write_json(path, payload)
        return path

    def artifact_manifest_path(
        self,
        workspace: RunWorkspace,
        artifact_id: str,
        version: str,
    ) -> Path:
        return workspace.artifacts_dir / f"{artifact_id}@{version}" / "manifest.json"

    def resolve_storage_path(self, manifest_uri: str) -> Path:
        return self.settings.data_dir / manifest_uri

    def compute_digest(self, path: Path) -> tuple[str, int]:
        hasher = hashlib.sha256()
        if path.is_file():
            data = path.read_bytes()
            hasher.update(data)
            return f"sha256:{hasher.hexdigest()}", len(data)

        size = 0
        for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
            relative = file_path.relative_to(path).as_posix().encode("utf-8")
            content = file_path.read_bytes()
            hasher.update(relative)
            hasher.update(b"\x00")
            hasher.update(content)
            size += len(content)
        return f"sha256:{hasher.hexdigest()}", size
