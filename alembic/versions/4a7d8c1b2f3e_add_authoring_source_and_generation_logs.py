"""Add authoring source metadata and generation logs

Revision ID: 4a7d8c1b2f3e
Revises: 9f4c6f1d2d11
Create Date: 2026-03-11 10:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "4a7d8c1b2f3e"
down_revision = "9f4c6f1d2d11"
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
    if not _has_column("authoring_sessions", "source_type"):
        op.add_column(
            "authoring_sessions",
            sa.Column("source_type", sa.String(length=64), nullable=True),
        )
    if not _has_column("authoring_sessions", "source_payload_json"):
        op.add_column(
            "authoring_sessions",
            sa.Column("source_payload_json", sa.JSON(), nullable=True),
        )

    if not _has_column("authoring_drafts", "source_json"):
        op.add_column(
            "authoring_drafts",
            sa.Column("source_json", sa.JSON(), nullable=True),
        )

    if not _has_table("authoring_generation_logs"):
        op.create_table(
            "authoring_generation_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["authoring_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("authoring_generation_logs", op.f("ix_authoring_generation_logs_session_id")):
        op.create_index(
            op.f("ix_authoring_generation_logs_session_id"),
            "authoring_generation_logs",
            ["session_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_authoring_generation_logs_session_id"), table_name="authoring_generation_logs")
    op.drop_table("authoring_generation_logs")
    op.drop_column("authoring_drafts", "source_json")
    op.drop_column("authoring_sessions", "source_payload_json")
    op.drop_column("authoring_sessions", "source_type")
