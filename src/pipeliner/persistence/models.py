from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pipeliner.db import Base


class AuthoringSessionModel(Base):
    __tablename__ = "authoring_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    intent_brief: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), index=True, default="active")  # active, published, discarded
    published_workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    drafts: Mapped[list[AuthoringDraftModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AuthoringDraftModel.revision"
    )
    messages: Mapped[list[AuthoringMessageModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AuthoringMessageModel.created_at"
    )
    generation_logs: Mapped[list[AuthoringGenerationLogModel]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AuthoringGenerationLogModel.created_at"
    )

class AuthoringDraftModel(Base):
    __tablename__ = "authoring_drafts"
    __table_args__ = (
        UniqueConstraint("session_id", "revision", name="uq_session_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("authoring_sessions.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    workflow_view_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lint_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lint_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    session: Mapped[AuthoringSessionModel] = relationship(back_populates="drafts")


class AuthoringMessageModel(Base):
    __tablename__ = "authoring_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("authoring_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    session: Mapped[AuthoringSessionModel] = relationship(back_populates="messages")


class AuthoringGenerationLogModel(Base):
    __tablename__ = "authoring_generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("authoring_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    session: Mapped[AuthoringSessionModel] = relationship(back_populates="generation_logs")

class WorkflowDefinitionModel(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list[WorkflowVersionModel]] = relationship(
        back_populates="workflow_definition", cascade="all, delete-orphan"
    )


class WorkflowVersionModel(Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_definition_id",
            "version",
            name="uq_workflow_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_definition_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(128))
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    lint_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    workflow_definition: Mapped[WorkflowDefinitionModel] = relationship(
        back_populates="versions"
    )
    runs: Mapped[list[RunModel]] = relationship(back_populates="workflow_version_rel")


class RunModel(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_version_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="RESTRICT"), index=True
    )
    workflow_id: Mapped[str] = mapped_column(String(255), index=True)
    workflow_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), index=True)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    workspace_root: Mapped[str] = mapped_column(String(512))
    stop_reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workflow_version_rel: Mapped[WorkflowVersionModel] = relationship(back_populates="runs")
    node_runs: Mapped[list[NodeRunModel]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    callback_events: Mapped[list[CallbackEventModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[ArtifactModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class BatchRunModel(Base):
    __tablename__ = "batch_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(255), index=True)
    workflow_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["BatchRunItemModel"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="BatchRunItemModel.row_index",
    )


class BatchRunItemModel(Base):
    __tablename__ = "batch_run_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_index", name="uq_batch_row"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batch_runs.id", ondelete="CASCADE"), index=True)
    row_index: Mapped[int] = mapped_column(Integer)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    batch: Mapped[BatchRunModel] = relationship(back_populates="items")


class NodeRunModel(Base):
    __tablename__ = "node_runs"
    __table_args__ = (
        UniqueConstraint("run_id", "node_id", "round_no", name="uq_node_round"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(255), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(64), index=True)
    waiting_for_role: Mapped[str | None] = mapped_column(String(32), default=None)
    stop_reason: Mapped[str | None] = mapped_column(Text, default=None)
    rework_brief_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    run: Mapped[RunModel] = relationship(back_populates="node_runs")


class CallbackEventModel(Base):
    __tablename__ = "callback_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(255), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    actor_role: Mapped[str] = mapped_column(String(32), index=True)
    validator_id: Mapped[str | None] = mapped_column(String(255), default=None)
    execution_status: Mapped[str] = mapped_column(String(32))
    verdict_status: Mapped[str | None] = mapped_column(String(32), default=None)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run: Mapped[RunModel] = relationship(back_populates="callback_events")


class ArtifactModel(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_id", "version", name="uq_run_artifact_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(255), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(32))
    artifact_id: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(64))
    storage_backend: Mapped[str] = mapped_column(String(64))
    storage_uri: Mapped[str] = mapped_column(String(1024))
    digest: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run: Mapped[RunModel] = relationship(back_populates="artifacts")
