from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from pydantic import BaseModel, Field, field_validator, model_validator

from pipeliner.types import ActorRole, ArtifactKind, StorageBackend


class ArtifactRef(BaseModel):
    artifact_id: str
    version: str


class ProducedBy(BaseModel):
    run_id: str
    node_id: str
    round_no: int = Field(ge=1)
    role: ActorRole


class ArtifactStorage(BaseModel):
    backend: StorageBackend
    uri: str

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        if not value or value.startswith("/") or value.startswith("file://"):
            raise ValueError("local_fs artifact uri 必须是相对路径")
        normalized = PurePosixPath(value)
        if ".." in normalized.parts:
            raise ValueError("artifact uri 不允许包含父目录跳转")
        return normalized.as_posix()


class ArtifactIntegrity(BaseModel):
    digest: str
    size_bytes: int | None = Field(default=None, ge=0)


class ArtifactDescriptor(BaseModel):
    media_type: str | None = None
    entrypoint: str | None = None
    index_file: str | None = None
    item_count: int | None = Field(default=None, ge=0)


class ArtifactLineage(BaseModel):
    parent_artifacts: list[ArtifactRef] = Field(default_factory=list)


class ArtifactManifest(BaseModel):
    schema_version: str = "pipeliner.artifact/v1alpha1"
    artifact_id: str
    version: str
    kind: ArtifactKind
    produced_by: ProducedBy
    storage: ArtifactStorage
    integrity: ArtifactIntegrity
    created_at: datetime
    descriptor: ArtifactDescriptor | None = None
    lineage: ArtifactLineage | None = None

    @model_validator(mode="after")
    def validate_schema(self) -> "ArtifactManifest":
        if not self.schema_version.startswith("pipeliner.artifact/v1"):
            raise ValueError("暂不支持的 artifact schema_version")
        return self
