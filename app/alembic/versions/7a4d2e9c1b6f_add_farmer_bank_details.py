"""add farmer bank details

Revision ID: 7a4d2e9c1b6f
Revises: f9c2b741d603
Create Date: 2026-10-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a4d2e9c1b6f"
down_revision: Union[str, Sequence[str], None] = "f9c2b741d603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "farmers", sa.Column("account_number", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "farmers", sa.Column("bank_name", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("farmers", "bank_name")
    op.drop_column("farmers", "account_number")
