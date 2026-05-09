from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    station_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    altitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    coverage_radius: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    fly_height: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    antenna_hag: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    runway_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reflection_net_hag: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    center_antenna_h: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    b_antenna_h: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    b_to_center_distance: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    reflection_diameter: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    downward_angle: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    antenna_tag: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    distance_to_runway: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    distance_v_to_runway: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    distance_endo_runway: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    unit_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aircraft: Mapped[str | None] = mapped_column(String(100), nullable=True)
    antenna_height: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    station_sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    combine_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
