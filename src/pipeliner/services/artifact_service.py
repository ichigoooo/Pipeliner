from __future__ import annotations

from pipeliner.config import Settings, get_settings
from pipeliner.persistence.models import ArtifactModel
from pipeliner.persistence.repositories import ArtifactRepository, RunRepository
from pipeliner.protocols.artifact import ArtifactManifest, ArtifactRef
from pipeliner.services.errors import ConflictError, NotFoundError, ValidationError
from pipeliner.storage.local_fs import WorkspaceManager
from pipeliner.types import ArtifactKind


class ArtifactService:
    def __init__(self, artifact_repo: ArtifactRepository, run_repo: RunRepository, settings: Settings | None = None) -> None:
        self.artifact_repo = artifact_repo
        self.run_repo = run_repo
        self.settings = settings or get_settings()
        self.workspace = WorkspaceManager(self.settings)

    def publish_manifest(self, manifest: ArtifactManifest) -> tuple[ArtifactModel, bool]:
        run = self.run_repo.get_run(manifest.produced_by.run_id)
        if run is None:
            raise NotFoundError(f"未找到 run: {manifest.produced_by.run_id}")
        workspace = self.workspace.get_workspace(run.workflow_id, run.id)
        expected_prefix = f"{workspace.relative_root}/"
        if not manifest.storage.uri.startswith(expected_prefix):
            raise ValidationError("artifact 必须落在该 run 的 workspace 下")

        payload_path = self.workspace.resolve_storage_path(manifest.storage.uri)
        if manifest.kind == ArtifactKind.FILE and not payload_path.is_file():
            raise ValidationError(f"artifact payload 文件不存在: {payload_path}")
        if manifest.kind in {ArtifactKind.DIRECTORY, ArtifactKind.COLLECTION} and not payload_path.is_dir():
            raise ValidationError(f"artifact payload 目录不存在: {payload_path}")

        actual_digest, actual_size = self.workspace.compute_digest(payload_path)
        if manifest.integrity.digest != actual_digest:
            raise ValidationError("artifact digest 与实际内容不匹配")
        if manifest.integrity.size_bytes is not None and manifest.integrity.size_bytes != actual_size:
            raise ValidationError("artifact size_bytes 与实际内容不匹配")

        manifest_json = manifest.model_dump(mode="json")
        existing = self.artifact_repo.get_artifact(
            manifest.produced_by.run_id, manifest.artifact_id, manifest.version
        )
        if existing is not None:
            if existing.manifest_json != manifest_json:
                raise ConflictError("artifact 已发布且不可变，不能覆盖同版本 manifest")
            return existing, False

        artifact = ArtifactModel(
            run_id=manifest.produced_by.run_id,
            node_id=manifest.produced_by.node_id,
            round_no=manifest.produced_by.round_no,
            role=manifest.produced_by.role.value,
            artifact_id=manifest.artifact_id,
            version=manifest.version,
            kind=manifest.kind.value,
            storage_backend=manifest.storage.backend.value,
            storage_uri=manifest.storage.uri,
            digest=manifest.integrity.digest,
            size_bytes=actual_size,
            manifest_json=manifest_json,
        )
        created = self.artifact_repo.create_artifact(artifact)
        manifest_path = self.workspace.artifact_manifest_path(workspace, manifest.artifact_id, manifest.version)
        self.workspace.write_json(manifest_path, manifest_json)
        return created, True

    def resolve_ref(self, run_id: str, ref: ArtifactRef) -> ArtifactManifest:
        artifact = self.artifact_repo.get_artifact(run_id, ref.artifact_id, ref.version)
        if artifact is None:
            raise NotFoundError(f"未找到 artifact: {ref.artifact_id}@{ref.version}")
        return ArtifactManifest.model_validate(artifact.manifest_json)

    def list_run_artifacts(self, run_id: str) -> list[ArtifactModel]:
        return self.artifact_repo.list_run_artifacts(run_id)

    def get_latest_node_artifact(self, run_id: str, node_id: str, artifact_id: str) -> ArtifactModel | None:
        artifacts = [
            item
            for item in self.artifact_repo.list_run_artifacts(run_id)
            if item.node_id == node_id and item.artifact_id == artifact_id
        ]
        if not artifacts:
            return None
        artifacts.sort(key=lambda item: (item.round_no, item.created_at))
        return artifacts[-1]
