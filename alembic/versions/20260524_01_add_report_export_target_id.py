"""add report_export target_id

Revision ID: 4f58b37ee9ba
Revises: 20260517_01
Create Date: 2026-05-24 14:41:03.674969
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f58b37ee9ba'
down_revision: Union[str, None] = '20260517_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("report_exports", sa.Column("target_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("report_exports", "target_id")
