"""增加导出任务表

Revision ID: 20260416_01
Revises: 20260414_03
Create Date: 2026-04-16 10:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260416_01"
down_revision: str | None = "20260414_03"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_exports",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column(
            "analysis_task_id",
            sa.String(length=100),
            sa.ForeignKey("analysis_tasks.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status_message",
            sa.String(length=255),
            nullable=False,
            server_default="export task created",
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("report_exports", "progress_percent", server_default=None)
    op.alter_column("report_exports", "status_message", server_default=None)


def downgrade() -> None:
    op.drop_table("report_exports")
