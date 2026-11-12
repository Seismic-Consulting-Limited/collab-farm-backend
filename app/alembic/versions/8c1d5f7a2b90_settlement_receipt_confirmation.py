"""add cooperative return reporting and admin receipt confirmation

Revision ID: 8c1d5f7a2b90
Revises: 6f2a9c1d4e80
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c1d5f7a2b90"
down_revision: Union[str, Sequence[str], None] = "6f2a9c1d4e80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "settlements",
        sa.Column("return_reported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("settlements", sa.Column("return_note", sa.String(), nullable=True))
    op.add_column("settlements", sa.Column("review_note", sa.String(), nullable=True))
    op.add_column("settlements", sa.Column("returned_by_id", sa.UUID(), nullable=True))
    op.add_column(
        "settlements", sa.Column("receipt_verified_by_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "settlements_returned_by_id_fkey",
        "settlements",
        "users",
        ["returned_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "settlements_receipt_verified_by_id_fkey",
        "settlements",
        "users",
        ["receipt_verified_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE settlements
        SET status = 'ONGOING', date_settled = NULL
        WHERE status IN ('DISBURSED', 'PENDING')
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "settlements_receipt_verified_by_id_fkey", "settlements", type_="foreignkey"
    )
    op.drop_constraint(
        "settlements_returned_by_id_fkey", "settlements", type_="foreignkey"
    )
    op.drop_column("settlements", "receipt_verified_by_id")
    op.drop_column("settlements", "returned_by_id")
    op.drop_column("settlements", "review_note")
    op.drop_column("settlements", "return_note")
    op.drop_column("settlements", "return_reported_at")
