"""replace_dates_with_tenure_and_roi_in_package_farmers

Revision ID: a05f3c666813
Revises: febbe432f480
Create Date: 2026-10-19 11:10:51.948818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a05f3c666813'
down_revision: Union[str, Sequence[str], None] = 'febbe432f480'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tenure_months and expected_roi with server_default to handle existing rows
    op.add_column(
        'package_farmers', 
        sa.Column('tenure_months', sa.Integer(), server_default='0', nullable=False)
    )
    op.add_column(
        'package_farmers', 
        sa.Column('expected_roi', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False)
    )
    op.drop_column('package_farmers', 'payback_date')
    op.drop_column('package_farmers', 'payout_date')
    op.drop_column('users', 'email_otp_expires_at')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'users', 
        sa.Column('email_otp_expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'package_farmers', 
        sa.Column('payout_date', sa.DATE(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'package_farmers', 
        sa.Column('payback_date', sa.DATE(), autoincrement=False, nullable=True)
    )
    op.drop_column('package_farmers', 'expected_roi')
    op.drop_column('package_farmers', 'tenure_months')