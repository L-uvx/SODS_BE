"""将障碍物几何列调整为通用 geometry

Revision ID: 20260427_01
Revises: 20260416_01
Create Date: 2026-04-27 10:00:00
"""

from collections.abc import Sequence

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa


revision: str = "20260427_01"
down_revision: str | None = "20260416_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "obstacles",
        "geom",
        existing_type=Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        type_=Geometry(geometry_type="GEOMETRY", srid=4326),
        existing_nullable=True,
        postgresql_using="geom::geometry(GEOMETRY,4326)",
    )


def downgrade() -> None:
    bind = op.get_bind()
    point_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM obstacles WHERE geom IS NOT NULL AND GeometryType(geom) <> 'MULTIPOLYGON'"
        )
    ).scalar_one()
    if point_count > 0:
        raise RuntimeError(
            "cannot downgrade obstacles.geom to MULTIPOLYGON while non-multipolygon rows exist"
        )

    op.alter_column(
        "obstacles",
        "geom",
        existing_type=Geometry(geometry_type="GEOMETRY", srid=4326),
        type_=Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        existing_nullable=True,
        postgresql_using="geom::geometry(MULTIPOLYGON,4326)",
    )
