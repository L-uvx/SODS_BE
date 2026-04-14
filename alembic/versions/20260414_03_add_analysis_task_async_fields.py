"""增加分析任务异步状态字段

Revision ID: 20260414_03
Revises: 20260414_02
Create Date: 2026-04-14 18:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_03"
down_revision: str | None = "20260414_02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_tasks",
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "analysis_tasks",
        sa.Column(
            "status_message",
            sa.String(length=255),
            nullable=False,
            server_default="analysis task created",
        ),
    )
    op.add_column(
        "analysis_tasks",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )
    op.alter_column("analysis_tasks", "progress_percent", server_default=None)
    op.alter_column("analysis_tasks", "status_message", server_default=None)


def downgrade() -> None:
    op.drop_column("analysis_tasks", "error_message")
    op.drop_column("analysis_tasks", "status_message")
    op.drop_column("analysis_tasks", "progress_percent")
