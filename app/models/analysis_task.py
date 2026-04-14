from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    import_batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    progress_percent: Mapped[int] = mapped_column(nullable=False, default=0)
    status_message: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    selected_target_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
