"""add package admin and cooperative review workflow

Revision ID: 4d8a1f3c6b20
Revises: 3a7c2e9f1b64
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d8a1f3c6b20"
down_revision: Union[str, Sequence[str], None] = "3a7c2e9f1b64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packages",
        sa.Column(
            "review_status",
            sa.String(length=30),
            server_default="PENDING_ADMIN",
            nullable=False,
        ),
    )
    op.add_column("packages", sa.Column("review_note", sa.String(), nullable=True))
    op.add_column("packages", sa.Column("cooperative_note", sa.String(), nullable=True))
    op.add_column("packages", sa.Column("proposed_changes", sa.JSON(), nullable=True))
    op.execute(
        """
        UPDATE packages
        SET review_status = CASE
            WHEN status = 'ACTIVE' THEN 'APPROVED'
            ELSE 'PENDING_ADMIN'
        END
        """
    )
    op.alter_column("packages", "review_status", server_default=None)


def downgrade() -> None:
    op.drop_column("packages", "proposed_changes")
    op.drop_column("packages", "review_note")
    op.drop_column("packages", "cooperative_note")
    op.drop_column("packages", "review_status")
