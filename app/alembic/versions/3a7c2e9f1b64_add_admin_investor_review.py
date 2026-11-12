"""add admin investor review note and make investor profiles pending

Revision ID: 3a7c2e9f1b64
Revises: 9e3b1a7c5d42
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7c2e9f1b64"
down_revision: Union[str, Sequence[str], None] = "9e3b1a7c5d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verification_note", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET verification_status = 'PENDING'
        WHERE role = 'INVESTOR'
          AND verification_status = 'APPROVED'
          AND (
              EXISTS (SELECT 1 FROM individual_profiles WHERE individual_profiles.user_id = users.id)
              OR EXISTS (SELECT 1 FROM group_profiles WHERE group_profiles.user_id = users.id)
          )
        """
    )


def downgrade() -> None:
    op.drop_column("users", "verification_note")
