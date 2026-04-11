"""新增机场跑道台站基础表

Revision ID: 20260411_01
Revises: 20260409_01
Create Date: 2026-04-11 20:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260411_01"
down_revision: str | None = "20260409_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "airports",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("longitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("latitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("altitude", sa.Numeric(10, 3), nullable=True),
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
        "runways",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_number", sa.String(length=100), nullable=True),
        sa.Column("direction", sa.Numeric(10, 2), nullable=True),
        sa.Column("length", sa.Numeric(10, 2), nullable=True),
        sa.Column("width", sa.Numeric(10, 2), nullable=True),
        sa.Column("enter_height", sa.Numeric(10, 2), nullable=True),
        sa.Column("maximum_airworthiness", sa.Numeric(10, 2), nullable=True),
        sa.Column("longitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("latitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("altitude", sa.Numeric(10, 3), nullable=True),
        sa.Column("station_sub_type", sa.String(length=100), nullable=True),
        sa.Column("runway_code_a", sa.String(length=100), nullable=True),
        sa.Column("runway_type", sa.String(length=100), nullable=True),
        sa.Column("runway_code_b", sa.String(length=100), nullable=True),
        sa.Column(
            "airport_id", sa.Integer(), sa.ForeignKey("airports.id"), nullable=False
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

    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("station_type", sa.String(length=100), nullable=True),
        sa.Column("station_group", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("frequency", sa.Numeric(10, 2), nullable=True),
        sa.Column("longitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("latitude", sa.Numeric(12, 6), nullable=True),
        sa.Column("altitude", sa.Numeric(10, 3), nullable=True),
        sa.Column("coverage_radius", sa.Numeric(10, 2), nullable=True),
        sa.Column("fly_height", sa.Numeric(10, 2), nullable=True),
        sa.Column("antenna_hag", sa.Numeric(10, 2), nullable=True),
        sa.Column("runway_no", sa.String(length=100), nullable=True),
        sa.Column("reflection_net_hag", sa.Numeric(10, 2), nullable=True),
        sa.Column("center_antenna_h", sa.Numeric(10, 2), nullable=True),
        sa.Column("b_antenna_h", sa.Numeric(10, 2), nullable=True),
        sa.Column("b_to_center_distance", sa.Numeric(10, 2), nullable=True),
        sa.Column("reflection_diameter", sa.Numeric(10, 2), nullable=True),
        sa.Column("downward_angle", sa.Numeric(10, 2), nullable=True),
        sa.Column("antenna_tag", sa.Numeric(10, 2), nullable=True),
        sa.Column("distance_to_runway", sa.Numeric(10, 2), nullable=True),
        sa.Column("distance_v_to_runway", sa.Numeric(10, 2), nullable=True),
        sa.Column("distance_endo_runway", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit_number", sa.String(length=100), nullable=True),
        sa.Column("aircraft", sa.String(length=100), nullable=True),
        sa.Column("antenna_height", sa.Numeric(10, 2), nullable=True),
        sa.Column("station_sub_type", sa.String(length=100), nullable=True),
        sa.Column(
            "airport_id", sa.Integer(), sa.ForeignKey("airports.id"), nullable=False
        ),
        sa.Column("combine_id", sa.String(length=100), nullable=True),
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
    op.drop_table("stations")
    op.drop_table("runways")
    op.drop_table("airports")
