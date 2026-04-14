"""增加导入任务异步字段

Revision ID: 20260414_02
Revises: 20260414_01
Create Date: 2026-04-14 14:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_02"
down_revision: str | None = "20260414_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "import_batches",
        sa.Column("source_file_path", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column("status_message", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("import_batches", "status_message")
    op.drop_column("import_batches", "progress_percent")
    op.drop_column("import_batches", "source_file_path")
