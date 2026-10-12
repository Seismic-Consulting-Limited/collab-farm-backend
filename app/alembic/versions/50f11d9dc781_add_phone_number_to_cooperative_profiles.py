"""add phone number to cooperative profiles

Revision ID: 50f11d9dc781
Revises: 793e494d6da9
Create Date: 2026-09-22 16:57:49.432303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '50f11d9dc781'
down_revision: Union[str, Sequence[str], None] = '793e494d6da9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Only add the phone number column safely ###
    # Change nullable to True initially so existing rows don't break
    op.add_column('cooperative_profiles', sa.Column('phone_number', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### Only drop the phone number column if rolling back ###
    op.drop_column('cooperative_profiles', 'phone_number')
    # ### end Alembic commands ###
