from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Runway(Base):
    __tablename__ = "runways"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direction: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    length: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    enter_height: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    maximum_airworthiness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    altitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    station_sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    runway_code_a: Mapped[str | None] = mapped_column(String(100), nullable=True)
    runway_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    runway_code_b: Mapped[str | None] = mapped_column(String(100), nullable=True)
    airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
