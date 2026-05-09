from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    altitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
