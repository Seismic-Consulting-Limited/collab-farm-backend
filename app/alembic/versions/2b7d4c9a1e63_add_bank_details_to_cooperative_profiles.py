"""add bank account details to cooperative profiles

Revision ID: 2b7d4c9a1e63
Revises: df217e8109de
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7d4c9a1e63"
down_revision: Union[str, Sequence[str], None] = ("df217e8109de", "3c8e21a76f45")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cooperative_profiles", sa.Column("account_number", sa.String(length=32), nullable=True))
    op.add_column("cooperative_profiles", sa.Column("bank_name", sa.String(length=120), nullable=True))
    op.add_column("cooperative_profiles", sa.Column("account_name", sa.String(length=160), nullable=True))


def downgrade() -> None:
    op.drop_column("cooperative_profiles", "account_name")
    op.drop_column("cooperative_profiles", "bank_name")
    op.drop_column("cooperative_profiles", "account_number")
