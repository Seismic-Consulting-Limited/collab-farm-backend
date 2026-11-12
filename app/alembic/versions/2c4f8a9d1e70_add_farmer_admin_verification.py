"""add farmer admin verification status and review note

Revision ID: 2c4f8a9d1e70
Revises: f9c2b741d603
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c4f8a9d1e70"
down_revision: Union[str, Sequence[str], None] = "f9c2b741d603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "farmers",
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="PENDING",
            nullable=False,
        ),
    )
    op.add_column("farmers", sa.Column("verification_note", sa.String(), nullable=True))
    # Existing farmer records were auto-verified on registration and need admin review.
    op.execute("UPDATE farmers SET verification_status = 'PENDING'")
    op.alter_column("farmers", "verification_status", server_default=None)


def downgrade() -> None:
    op.drop_column("farmers", "verification_note")
    op.drop_column("farmers", "verification_status")
