"""add unique short package codes

Revision ID: 3c8e21a76f45
Revises: 7a4d2e9c1b6f
Create Date: 2026-10-28

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c8e21a76f45"
down_revision: Union[str, Sequence[str], None] = "7a4d2e9c1b6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packages",
        sa.Column("package_code", sa.String(length=20), nullable=True),
    )

    packages = sa.table(
        "packages",
        sa.column("id", sa.Uuid()),
        sa.column("package_code", sa.String(length=20)),
    )
    connection = op.get_bind()
    package_ids = connection.execute(sa.select(packages.c.id)).scalars().all()
    for package_id in package_ids:
        connection.execute(
            sa.update(packages)
            .where(packages.c.id == package_id)
            .values(package_code=f"PKG-{uuid.uuid4().hex[:12].upper()}")
        )

    op.alter_column("packages", "package_code", nullable=False)
    op.create_unique_constraint(
        "uq_packages_package_code", "packages", ["package_code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_packages_package_code", "packages", type_="unique")
    op.drop_column("packages", "package_code")
