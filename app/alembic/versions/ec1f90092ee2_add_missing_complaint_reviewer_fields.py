"""add_missing_complaint_reviewer_fields

Revision ID: ec1f90092ee2
Revises: 8c1d5f7a2b90
Create Date: 2026-11-12 15:57:30.500077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ec1f90092ee2'
down_revision: Union[str, Sequence[str], None] = '8c1d5f7a2b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {col["name"] for col in inspector.get_columns("complaints")}

    if "assigned_reviewer_id" not in existing_columns:
        op.add_column(
            "complaints",
            sa.Column("assigned_reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "complaints_assigned_reviewer_id_fkey",
            "complaints",
            "users",
            ["assigned_reviewer_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "outcome" not in existing_columns:
        op.add_column(
            "complaints",
            sa.Column("outcome", sa.String(length=40), nullable=True),
        )

    if "explanation" not in existing_columns:
        op.add_column(
            "complaints",
            sa.Column("explanation", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {col["name"] for col in inspector.get_columns("complaints")}

    if "assigned_reviewer_id" in existing_columns:
        op.drop_constraint("complaints_assigned_reviewer_id_fkey", "complaints", type_="foreignkey")
        op.drop_column("complaints", "assigned_reviewer_id")

    if "outcome" in existing_columns:
        op.drop_column("complaints", "outcome")

    if "explanation" in existing_columns:
        op.drop_column("complaints", "explanation")
