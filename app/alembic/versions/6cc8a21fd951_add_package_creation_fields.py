"""add package creation fields

Revision ID: 6cc8a21fd951
Revises: 2b7d4c9a1e63
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6cc8a21fd951"
down_revision: Union[str, Sequence[str], None] = "2b7d4c9a1e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("packages", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("packages", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("packages", sa.Column("funding_closes_on", sa.Date(), nullable=True))
    op.add_column("packages", sa.Column("minimum_funding_target", sa.Numeric(12, 2), nullable=True))
    op.add_column("packages", sa.Column("maximum_investment", sa.Numeric(12, 2), nullable=True))
    op.add_column("packages", sa.Column("minimum_investment", sa.Numeric(12, 2), nullable=True))
    op.add_column("packages", sa.Column("expected_output", sa.String(), nullable=True))
    op.add_column("packages", sa.Column("expected_return_min", sa.Float(), nullable=True))
    op.add_column("packages", sa.Column("expected_return_max", sa.Float(), nullable=True))

    op.execute("""
        UPDATE packages
        SET start_date = COALESCE(start_date, created_at::date),
            end_date = COALESCE(end_date, expected_payback_date),
            funding_closes_on = COALESCE(funding_closes_on, created_at::date),
            minimum_funding_target = COALESCE(minimum_funding_target, fund_amount),
            maximum_investment = COALESCE(maximum_investment, fund_amount),
            minimum_investment = COALESCE(minimum_investment, 1),
            expected_output = COALESCE(expected_output, 'Not specified'),
            expected_return_min = COALESCE(expected_return_min, expected_roi),
            expected_return_max = COALESCE(expected_return_max, expected_roi)
    """)
    for column in (
        "start_date", "end_date", "funding_closes_on", "minimum_funding_target",
        "maximum_investment", "minimum_investment", "expected_output",
        "expected_return_min", "expected_return_max",
    ):
        op.alter_column("packages", column, nullable=False)


def downgrade() -> None:
    op.drop_column("packages", "expected_return_max")
    op.drop_column("packages", "expected_return_min")
    op.drop_column("packages", "expected_output")
    op.drop_column("packages", "minimum_investment")
    op.drop_column("packages", "maximum_investment")
    op.drop_column("packages", "minimum_funding_target")
    op.drop_column("packages", "funding_closes_on")
    op.drop_column("packages", "end_date")
    op.drop_column("packages", "start_date")
