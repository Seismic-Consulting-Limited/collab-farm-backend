"""remove obsolete farmer WRS status

Revision ID: 9e3b1a7c5d42
Revises: 7b6e1a4d9c20
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e3b1a7c5d42"
down_revision: Union[str, Sequence[str], None] = "7b6e1a4d9c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("farmers", "wrs_status")


def downgrade() -> None:
    op.add_column(
        "farmers",
        sa.Column("wrs_status", sa.String(), server_default="VERIFIED", nullable=False),
    )
    op.alter_column("farmers", "wrs_status", server_default=None)
