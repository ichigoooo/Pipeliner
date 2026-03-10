"""Expand authoring models for workflow studio

Revision ID: 9f4c6f1d2d11
Revises: c6e2c87f35cd
Create Date: 2026-03-10 10:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9f4c6f1d2d11"
down_revision = "c6e2c87f35cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "authoring_sessions",
        sa.Column("published_workflow_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "authoring_sessions",
        sa.Column("published_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "authoring_sessions",
        sa.Column("published_revision", sa.Integer(), nullable=True),
    )
    op.add_column(
        "authoring_sessions",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "authoring_drafts",
        sa.Column("workflow_view_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "authoring_drafts",
        sa.Column("graph_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "authoring_drafts",
        sa.Column("lint_report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

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
    op.create_index(
        op.f("ix_authoring_messages_session_id"),
        "authoring_messages",
        ["session_id"],
        unique=False,
    )

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
