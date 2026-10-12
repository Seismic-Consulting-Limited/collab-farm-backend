"""drop email from cooperative_profiles

Revision ID: febbe432f480
Revises: 50f11d9dc781
Create Date: 2026-09-22 17:01:45.032967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'febbe432f480'
down_revision: Union[str, Sequence[str], None] = '50f11d9dc781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('cooperative_profiles', 'email')

def downgrade() -> None:
    op.add_column('cooperative_profiles', sa.Column('email', sa.String(), nullable=False))

