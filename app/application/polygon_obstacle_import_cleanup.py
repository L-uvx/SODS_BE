from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.import_batch import ImportBatch
from app.models.report_export import ReportExport


def cleanup_import_storage(settings: Settings, session: Session) -> None:
    storage_dir = settings.import_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    for task_directory in storage_dir.iterdir():
        if not task_directory.is_dir():
            continue

        import_batch = session.get(ImportBatch, task_directory.name)
        if import_batch is None:
            if _is_older_than_minutes(
                task_directory, settings.import_stale_retention_minutes
            ):
                shutil.rmtree(task_directory, ignore_errors=True)
            continue

        if _should_delete_import_directory(import_batch, settings):
            shutil.rmtree(task_directory, ignore_errors=True)


def cleanup_export_storage(settings: Settings, session: Session) -> None:
    storage_dir = settings.export_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    for task_directory in storage_dir.iterdir():
        if not task_directory.is_dir():
            continue

        report_export = session.get(ReportExport, task_directory.name)
        if report_export is None:
            if _is_older_than_minutes(
                task_directory, settings.export_stale_retention_minutes
            ):
                shutil.rmtree(task_directory, ignore_errors=True)
            continue

        if _should_delete_export_directory(report_export, settings):
            shutil.rmtree(task_directory, ignore_errors=True)


def _should_delete_import_directory(
    import_batch: ImportBatch,
    settings: Settings,
) -> bool:
    if import_batch.status == "succeeded":
        return _is_expired(
            import_batch.finished_at, settings.import_success_retention_minutes
        )

    if import_batch.status == "failed":
        return _is_expired(
            import_batch.finished_at, settings.import_failed_retention_minutes
        )

    if import_batch.status in {"pending", "running"}:
        reference_time = import_batch.started_at or import_batch.created_at
        return _is_expired(reference_time, settings.import_stale_retention_minutes)

    return False


def _should_delete_export_directory(
    report_export: ReportExport,
    settings: Settings,
) -> bool:
    if report_export.status == "succeeded":
        return _is_expired(
            report_export.finished_at, settings.export_success_retention_minutes
        )

    if report_export.status == "failed":
        return _is_expired(
            report_export.finished_at, settings.export_failed_retention_minutes
        )

    if report_export.status in {"pending", "running"}:
        return _is_expired(
            report_export.created_at, settings.export_stale_retention_minutes
        )

    return False


def _is_expired(reference_time: datetime | None, retention_minutes: int) -> bool:
    if reference_time is None:
        return False

    reference_time_utc = _as_utc(reference_time)
    return datetime.now(UTC) - reference_time_utc > timedelta(minutes=retention_minutes)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_older_than_minutes(path: Path, retention_minutes: int) -> bool:
    modified_time = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return datetime.now(UTC) - modified_time > timedelta(minutes=retention_minutes)
