"""Expand authoring models for workflow studio

Revision ID: 9f4c6f1d2d11
Revises: c6e2c87f35cd
Create Date: 2026-03-10 10:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "9f4c6f1d2d11"
down_revision = "c6e2c87f35cd"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in set(inspector.get_table_names())


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_column("authoring_sessions", "published_workflow_id"):
        op.add_column(
            "authoring_sessions",
            sa.Column("published_workflow_id", sa.String(length=255), nullable=True),
        )
    if not _has_column("authoring_sessions", "published_version"):
        op.add_column(
            "authoring_sessions",
            sa.Column("published_version", sa.String(length=64), nullable=True),
        )
    if not _has_column("authoring_sessions", "published_revision"):
        op.add_column(
            "authoring_sessions",
            sa.Column("published_revision", sa.Integer(), nullable=True),
        )
    if not _has_column("authoring_sessions", "published_at"):
        op.add_column(
            "authoring_sessions",
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column("authoring_drafts", "workflow_view_json"):
        op.add_column(
            "authoring_drafts",
            sa.Column("workflow_view_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
    if not _has_column("authoring_drafts", "graph_json"):
        op.add_column(
            "authoring_drafts",
            sa.Column("graph_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
    if not _has_column("authoring_drafts", "lint_report_json"):
        op.add_column(
            "authoring_drafts",
            sa.Column("lint_report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )

    if not _has_table("authoring_messages"):
        op.create_table(
            "authoring_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=True),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["authoring_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("authoring_messages", op.f("ix_authoring_messages_session_id")):
        op.create_index(
            op.f("ix_authoring_messages_session_id"),
            "authoring_messages",
            ["session_id"],
            unique=False,
        )

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column("authoring_drafts", "workflow_view_json", server_default=None)
        op.alter_column("authoring_drafts", "graph_json", server_default=None)
        op.alter_column("authoring_drafts", "lint_report_json", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_authoring_messages_session_id"), table_name="authoring_messages")
    op.drop_table("authoring_messages")
    op.drop_column("authoring_drafts", "lint_report_json")
    op.drop_column("authoring_drafts", "graph_json")
    op.drop_column("authoring_drafts", "workflow_view_json")
    op.drop_column("authoring_sessions", "published_at")
    op.drop_column("authoring_sessions", "published_revision")
    op.drop_column("authoring_sessions", "published_version")
    op.drop_column("authoring_sessions", "published_workflow_id")
