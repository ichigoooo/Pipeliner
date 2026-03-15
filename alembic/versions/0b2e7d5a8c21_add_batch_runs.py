"""Add batch run tracking tables

Revision ID: 0b2e7d5a8c21
Revises: 9f4c6f1d2d11
Create Date: 2026-03-15 10:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0b2e7d5a8c21"
down_revision = "9f4c6f1d2d11"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in set(inspector.get_table_names())


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("batch_runs"):
        op.create_table(
            "batch_runs",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("workflow_id", sa.String(length=255), nullable=False),
            sa.Column("workflow_version", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("batch_runs", op.f("ix_batch_runs_workflow_id")):
        op.create_index(op.f("ix_batch_runs_workflow_id"), "batch_runs", ["workflow_id"], unique=False)
    if not _has_index("batch_runs", op.f("ix_batch_runs_status")):
        op.create_index(op.f("ix_batch_runs_status"), "batch_runs", ["status"], unique=False)

    if not _has_table("batch_run_items"):
        op.create_table(
            "batch_run_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("batch_id", sa.String(length=64), nullable=False),
            sa.Column("row_index", sa.Integer(), nullable=False),
            sa.Column("inputs_json", sa.JSON(), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["batch_id"], ["batch_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("batch_id", "row_index", name="uq_batch_row"),
        )
    if not _has_index("batch_run_items", op.f("ix_batch_run_items_batch_id")):
        op.create_index(op.f("ix_batch_run_items_batch_id"), "batch_run_items", ["batch_id"], unique=False)
    if not _has_index("batch_run_items", op.f("ix_batch_run_items_run_id")):
        op.create_index(op.f("ix_batch_run_items_run_id"), "batch_run_items", ["run_id"], unique=False)
    if not _has_index("batch_run_items", op.f("ix_batch_run_items_status")):
        op.create_index(op.f("ix_batch_run_items_status"), "batch_run_items", ["status"], unique=False)

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column("batch_runs", "total_count", server_default=None)
        op.alter_column("batch_runs", "success_count", server_default=None)
        op.alter_column("batch_runs", "failed_count", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_batch_run_items_status"), table_name="batch_run_items")
    op.drop_index(op.f("ix_batch_run_items_run_id"), table_name="batch_run_items")
    op.drop_index(op.f("ix_batch_run_items_batch_id"), table_name="batch_run_items")
    op.drop_table("batch_run_items")
    op.drop_index(op.f("ix_batch_runs_status"), table_name="batch_runs")
    op.drop_index(op.f("ix_batch_runs_workflow_id"), table_name="batch_runs")
    op.drop_table("batch_runs")
