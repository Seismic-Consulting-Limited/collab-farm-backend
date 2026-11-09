"""add farmer identity and consent fields

Revision ID: 7de12ac840b6
Revises: 6cc8a21fd951
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7de12ac840b6"
down_revision: Union[str, Sequence[str], None] = "6cc8a21fd951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("farmers", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("farmers", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column("farmers", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("farmers", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("farmers", sa.Column("id_photo", sa.String(), nullable=True))
    op.add_column("farmers", sa.Column("years_of_experience", sa.Integer(), server_default="0", nullable=False))
    op.add_column("farmers", sa.Column("terms_accepted", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute("""
        UPDATE farmers
        SET first_name = COALESCE(first_name, split_part(full_name, ' ', 1)),
            last_name = COALESCE(last_name, NULLIF(trim(substr(full_name, length(split_part(full_name, ' ', 1)) + 1)), ''))
    """)
    op.alter_column("farmers", "phone_number", existing_type=sa.String(), nullable=True)
    op.alter_column("farmers", "years_of_experience", server_default=None)
    op.alter_column("farmers", "terms_accepted", server_default=None)


def downgrade() -> None:
    op.alter_column("farmers", "phone_number", existing_type=sa.String(), nullable=False)
    op.drop_column("farmers", "terms_accepted")
    op.drop_column("farmers", "years_of_experience")
    op.drop_column("farmers", "id_photo")
    op.drop_column("farmers", "email")
    op.drop_column("farmers", "date_of_birth")
    op.drop_column("farmers", "last_name")
    op.drop_column("farmers", "first_name")
