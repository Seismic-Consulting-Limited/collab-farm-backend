"""create user notifications

Revision ID: d431c8ef0b12
Revises: c2a4f9317b20
Create Date: 2026-11-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d431c8ef0b12"
down_revision: Union[str, Sequence[str], None] = "c2a4f9317b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("notification_type", sa.String(length=60), nullable=False),
            sa.Column("entity_type", sa.String(length=60), nullable=True),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("link", sa.String(length=500), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("notifications")}
    if "ix_notifications_recipient_id" not in indexes:
        op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    if "ix_notifications_created_at" not in indexes:
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("notifications"):
        for index in inspector.get_indexes("notifications"):
            if index["name"].startswith("ix_notifications"):
                op.drop_index(index["name"], table_name="notifications")
        op.drop_table("notifications")
