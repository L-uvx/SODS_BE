from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    analysis_task_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_tasks.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    progress_percent: Mapped[int] = mapped_column(nullable=False, default=0)
    status_message: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
