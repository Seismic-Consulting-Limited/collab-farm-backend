"""merge farmer verification and notifications migration heads

Revision ID: 7b6e1a4d9c20
Revises: 2c4f8a9d1e70, d431c8ef0b12
Create Date: 2026-11-12
"""
from typing import Sequence, Union


revision: str = "7b6e1a4d9c20"
down_revision: Union[str, Sequence[str], None] = (
    "2c4f8a9d1e70",
    "d431c8ef0b12",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
