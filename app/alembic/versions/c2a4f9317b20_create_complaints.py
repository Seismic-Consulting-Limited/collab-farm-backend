"""create complaints

Revision ID: c2a4f9317b20
Revises: 91f3a4c6d8e2
Create Date: 2026-11-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c2a4f9317b20"
down_revision: Union[str, Sequence[str], None] = "91f3a4c6d8e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("complaints"):
        op.create_table(
            "complaints",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reference", sa.String(length=20), nullable=False),
            sa.Column("submitted_by_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("subject", sa.String(length=200), nullable=False),
            sa.Column(
                "category",
                sa.Enum(
                    "PACKAGE", "INVESTMENT", "PAYMENT", "DELIVERY", "FARMER", "OTHER",
                    name="complaintcategory", native_enum=False,
                ),
                nullable=False,
            ),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "OPEN", "UNDER_REVIEW", "AWAITING_RESPONSE", "RESOLVED", "ESCALATED",
                    name="complaintstatus", native_enum=False,
                ),
                nullable=False,
                server_default="OPEN",
            ),
            sa.Column("acknowledgment_accepted", sa.Boolean(), nullable=False),
            sa.Column("assigned_reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("outcome", sa.String(length=40), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("reference"),
        )
    _create_index_if_missing("ix_complaints_submitted_by_id", "complaints", ["submitted_by_id"])
    _create_index_if_missing("ix_complaints_package_id", "complaints", ["package_id"])
    if not sa.inspect(op.get_bind()).has_table("complaint_messages"):
        op.create_table(
            "complaint_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_complaint_messages_complaint_id", "complaint_messages", ["complaint_id"]
    )
    if not sa.inspect(op.get_bind()).has_table("complaint_actions"):
        op.create_table(
            "complaint_actions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("complaint_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(
        "ix_complaint_actions_complaint_id", "complaint_actions", ["complaint_id"]
    )


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(table) and name not in {
        index["name"] for index in inspector.get_indexes(table)
    }:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for table in ("complaint_actions", "complaint_messages", "complaints"):
        inspector = sa.inspect(op.get_bind())
        if not inspector.has_table(table):
            continue
        for index in inspector.get_indexes(table):
            if index["name"].startswith("ix_complaint"):
                op.drop_index(index["name"], table_name=table)
        op.drop_table(table)
