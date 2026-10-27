"""add unique farmer loan codes to disbursements

Revision ID: f9c2b741d603
Revises: ca834eb2eb48
Create Date: 2026-10-27

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c2b741d603"
down_revision: Union[str, Sequence[str], None] = "ca834eb2eb48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "disbursements",
        sa.Column("loan_code", sa.String(length=40), nullable=True),
    )

    disbursements = sa.table(
        "disbursements",
        sa.column("id", sa.Uuid()),
        sa.column("loan_code", sa.String(length=40)),
    )
    connection = op.get_bind()
    existing_ids = connection.execute(
        sa.select(disbursements.c.id)
    ).scalars().all()
    for disbursement_id in existing_ids:
        connection.execute(
            sa.update(disbursements)
            .where(disbursements.c.id == disbursement_id)
            .values(loan_code=f"FL-{uuid.uuid4().hex.upper()}")
        )

    op.alter_column("disbursements", "loan_code", nullable=False)
    op.create_unique_constraint(
        "uq_disbursements_loan_code", "disbursements", ["loan_code"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_disbursements_loan_code", "disbursements", type_="unique"
    )
    op.drop_column("disbursements", "loan_code")
