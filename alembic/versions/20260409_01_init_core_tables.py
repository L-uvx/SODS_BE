"""初始化核心业务表结构

Revision ID: 20260409_01
Revises:
Create Date: 2026-04-09 16:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision: str = "20260409_01"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
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
    )

    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("import_type", sa.String(length=50), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "obstacles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("obstacle_type", sa.String(length=100), nullable=True),
        sa.Column("source_batch_id", sa.String(length=100), nullable=True),
        sa.Column("source_row_no", sa.Integer(), nullable=True),
        sa.Column("top_elevation", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True
        ),
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
    )


def downgrade() -> None:
    op.drop_table("obstacles")
    op.drop_table("import_batches")
    op.drop_table("projects")
