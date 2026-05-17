"""添加跑道最大适航机型字段

Revision ID: 20260517_01
Revises: 20260509_01
Create Date: 2026-05-17 10:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260517_01"
down_revision: str | None = "20260509_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runways",
        sa.Column("maximum_type_aircraft", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("runways", "maximum_type_aircraft")
