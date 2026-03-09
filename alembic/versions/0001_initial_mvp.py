"""initial mvp schema"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_mvp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workflow_id"),
    )
    op.create_index("ix_workflow_definitions_workflow_id", "workflow_definitions", ["workflow_id"])

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_definition_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=128), nullable=False),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("lint_warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_definition_id"], ["workflow_definitions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow_definition_id", "version", name="uq_workflow_version"),
    )
    op.create_index("ix_workflow_versions_workflow_definition_id", "workflow_versions", ["workflow_definition_id"])

    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workflow_version_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("inputs_json", sa.JSON(), nullable=False),
        sa.Column("workspace_root", sa.String(length=512), nullable=False),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_runs_workflow_version_id", "runs", ["workflow_version_id"])
    op.create_index("ix_runs_workflow_id", "runs", ["workflow_id"])
    op.create_index("ix_runs_status", "runs", ["status"])

    op.create_table(
        "node_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("waiting_for_role", sa.String(length=32), nullable=True),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("rework_brief_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "node_id", "round_no", name="uq_node_round"),
    )
    op.create_index("ix_node_runs_run_id", "node_runs", ["run_id"])
    op.create_index("ix_node_runs_node_id", "node_runs", ["node_id"])
    op.create_index("ix_node_runs_status", "node_runs", ["status"])

    op.create_table(
        "callback_events",
        sa.Column("event_id", sa.String(length=255), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("validator_id", sa.String(length=255), nullable=True),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("verdict_status", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_callback_events_run_id", "callback_events", ["run_id"])
    op.create_index("ix_callback_events_node_id", "callback_events", ["node_id"])
    op.create_index("ix_callback_events_actor_role", "callback_events", ["actor_role"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("artifact_id", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("storage_backend", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "artifact_id", "version", name="uq_run_artifact_version"),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("ix_artifacts_node_id", "artifacts", ["node_id"])
    op.create_index("ix_artifacts_artifact_id", "artifacts", ["artifact_id"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_artifact_id", table_name="artifacts")
    op.drop_index("ix_artifacts_node_id", table_name="artifacts")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_callback_events_actor_role", table_name="callback_events")
    op.drop_index("ix_callback_events_node_id", table_name="callback_events")
    op.drop_index("ix_callback_events_run_id", table_name="callback_events")
    op.drop_table("callback_events")

    op.drop_index("ix_node_runs_status", table_name="node_runs")
    op.drop_index("ix_node_runs_node_id", table_name="node_runs")
    op.drop_index("ix_node_runs_run_id", table_name="node_runs")
    op.drop_table("node_runs")

    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_workflow_id", table_name="runs")
    op.drop_index("ix_runs_workflow_version_id", table_name="runs")
    op.drop_table("runs")

    op.drop_index("ix_workflow_versions_workflow_definition_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")

    op.drop_index("ix_workflow_definitions_workflow_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
