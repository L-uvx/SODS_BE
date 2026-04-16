from datetime import UTC, datetime, timedelta
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.analysis_task import AnalysisTask
from app.models.import_batch import ImportBatch
from app.models.project import Project
from app.models.report_export import ReportExport


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Project.__table__,
            ImportBatch.__table__,
            AnalysisTask.__table__,
            ReportExport.__table__,
        ],
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local()


def _build_settings(tmp_path: Path):
    from app.core.config import Settings

    return Settings(
        app_env="test",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        import_storage_dir=tmp_path / "imports",
        import_success_retention_minutes=10,
        import_failed_retention_minutes=30,
        import_stale_retention_minutes=30,
        export_storage_dir=tmp_path / "exports",
        export_success_retention_minutes=10,
        export_failed_retention_minutes=30,
        export_stale_retention_minutes=30,
    )


def _create_analysis_task(session: Session) -> str:
    project = Project(name="demo")
    session.add(project)
    session.flush()
    session.add(
        ImportBatch(
            id="import-batch-1",
            project_id=project.id,
            status="succeeded",
            import_type="building",
            source_file_name="demo.xlsx",
            source_file_path="/tmp/demo.xlsx",
            progress_percent=100,
            status_message="import task succeeded",
        )
    )
    session.add(
        AnalysisTask(
            id="analysis-task-1",
            import_batch_id="import-batch-1",
            status="succeeded",
            progress_percent=100,
            status_message="analysis task succeeded",
            error_message=None,
            selected_target_ids=[1],
            result_payload={"summary": "done"},
        )
    )
    session.commit()
    return "analysis-task-1"


def test_cleanup_export_storage_removes_expired_succeeded_directory(
    tmp_path: Path,
) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_export_storage

    session = _create_session()
    analysis_task_id = _create_analysis_task(session)
    task_directory = (tmp_path / "exports") / "export-task-1"
    task_directory.mkdir(parents=True)
    file_path = task_directory / "report.docx"
    file_path.write_bytes(b"demo")
    session.add(
        ReportExport(
            id="export-task-1",
            analysis_task_id=analysis_task_id,
            status="succeeded",
            progress_percent=100,
            status_message="export task succeeded",
            error_message=None,
            file_name="report.docx",
            file_path=str(file_path),
            finished_at=datetime.now(UTC) - timedelta(minutes=11),
        )
    )
    session.commit()

    cleanup_export_storage(_build_settings(tmp_path), session)

    assert not task_directory.exists()


def test_cleanup_export_storage_removes_expired_failed_directory(
    tmp_path: Path,
) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_export_storage

    session = _create_session()
    analysis_task_id = _create_analysis_task(session)
    task_directory = (tmp_path / "exports") / "export-task-2"
    task_directory.mkdir(parents=True)
    file_path = task_directory / "report.docx"
    file_path.write_bytes(b"demo")
    session.add(
        ReportExport(
            id="export-task-2",
            analysis_task_id=analysis_task_id,
            status="failed",
            progress_percent=100,
            status_message="export task failed",
            error_message="boom",
            file_name="report.docx",
            file_path=str(file_path),
            finished_at=datetime.now(UTC) - timedelta(minutes=31),
        )
    )
    session.commit()

    cleanup_export_storage(_build_settings(tmp_path), session)

    assert not task_directory.exists()


def test_cleanup_export_storage_keeps_fresh_running_directory(tmp_path: Path) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_export_storage

    session = _create_session()
    analysis_task_id = _create_analysis_task(session)
    task_directory = (tmp_path / "exports") / "export-task-3"
    task_directory.mkdir(parents=True)
    file_path = task_directory / "report.docx"
    file_path.write_bytes(b"demo")
    session.add(
        ReportExport(
            id="export-task-3",
            analysis_task_id=analysis_task_id,
            status="running",
            progress_percent=50,
            status_message="export task running",
            error_message=None,
            file_name="report.docx",
            file_path=str(file_path),
            created_at=datetime.now(UTC),
        )
    )
    session.commit()

    cleanup_export_storage(_build_settings(tmp_path), session)

    assert task_directory.exists()


def test_cleanup_export_storage_removes_orphan_directory(tmp_path: Path) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_export_storage

    session = _create_session()
    task_directory = (tmp_path / "exports") / "export-task-orphan"
    task_directory.mkdir(parents=True)
    file_path = task_directory / "report.docx"
    file_path.write_bytes(b"demo")
    stale_timestamp = (datetime.now() - timedelta(minutes=31)).timestamp()
    os.utime(task_directory, (stale_timestamp, stale_timestamp))
    os.utime(file_path, (stale_timestamp, stale_timestamp))

    cleanup_export_storage(_build_settings(tmp_path), session)

    assert not task_directory.exists()
