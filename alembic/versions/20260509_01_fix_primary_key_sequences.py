"""修复主键序列使与现有数据对齐

Revision ID: 20260509_01
Revises: 20260427_01
Create Date: 2026-05-09 10:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260509_01"
down_revision: str | None = "20260427_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "SELECT setval(pg_get_serial_sequence('airports', 'id'), "
        "COALESCE(MAX(id), 1)) FROM airports"
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('runways', 'id'), "
        "COALESCE(MAX(id), 1)) FROM runways"
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('stations', 'id'), "
        "COALESCE(MAX(id), 1)) FROM stations"
    )


def downgrade() -> None:
    pass
