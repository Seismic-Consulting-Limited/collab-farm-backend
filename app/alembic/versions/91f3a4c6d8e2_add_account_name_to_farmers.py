"""add account name to farmers

Revision ID: 91f3a4c6d8e2
Revises: 7de12ac840b6
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91f3a4c6d8e2"
down_revision: Union[str, Sequence[str], None] = "7de12ac840b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("farmers", sa.Column("account_name", sa.String(length=160), nullable=True))


def downgrade() -> None:
    op.drop_column("farmers", "account_name")
