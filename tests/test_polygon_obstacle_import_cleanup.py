from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.import_batch import ImportBatch
from app.models.project import Project


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine, tables=[Project.__table__, ImportBatch.__table__]
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local()


def test_cleanup_import_storage_removes_expired_succeeded_directory(
    tmp_path: Path,
) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
    from app.core.config import Settings

    session = _create_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()

    task_directory = tmp_path / "import-batch-1"
    task_directory.mkdir(parents=True)
    source_file_path = task_directory / "demo.xlsx"
    source_file_path.write_bytes(b"demo")
    session.add(
        ImportBatch(
            id="import-batch-1",
            project_id=project.id,
            status="succeeded",
            import_type="building",
            source_file_name="demo.xlsx",
            source_file_path=str(source_file_path),
            progress_percent=100,
            status_message="import task succeeded",
            finished_at=datetime.now(UTC) - timedelta(minutes=11),
        )
    )
    session.commit()

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        import_storage_dir=tmp_path,
        import_success_retention_minutes=10,
        import_failed_retention_minutes=30,
        import_stale_retention_minutes=30,
    )

    cleanup_import_storage(settings, session)

    assert not task_directory.exists()


def test_cleanup_import_storage_removes_expired_failed_directory(
    tmp_path: Path,
) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
    from app.core.config import Settings

    session = _create_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()

    task_directory = tmp_path / "import-batch-2"
    task_directory.mkdir(parents=True)
    source_file_path = task_directory / "demo.xlsx"
    source_file_path.write_bytes(b"demo")
    session.add(
        ImportBatch(
            id="import-batch-2",
            project_id=project.id,
            status="failed",
            import_type="building",
            source_file_name="demo.xlsx",
            source_file_path=str(source_file_path),
            progress_percent=100,
            status_message="import task failed",
            finished_at=datetime.now(UTC) - timedelta(minutes=31),
        )
    )
    session.commit()

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        import_storage_dir=tmp_path,
        import_success_retention_minutes=10,
        import_failed_retention_minutes=30,
        import_stale_retention_minutes=30,
    )

    cleanup_import_storage(settings, session)

    assert not task_directory.exists()


def test_cleanup_import_storage_keeps_fresh_pending_directory(tmp_path: Path) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
    from app.core.config import Settings

    session = _create_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()

    task_directory = tmp_path / "import-batch-3"
    task_directory.mkdir(parents=True)
    source_file_path = task_directory / "demo.xlsx"
    source_file_path.write_bytes(b"demo")
    session.add(
        ImportBatch(
            id="import-batch-3",
            project_id=project.id,
            status="pending",
            import_type="building",
            source_file_name="demo.xlsx",
            source_file_path=str(source_file_path),
            progress_percent=0,
            status_message="import task created",
            created_at=datetime.now(UTC),
        )
    )
    session.commit()

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        import_storage_dir=tmp_path,
        import_success_retention_minutes=10,
        import_failed_retention_minutes=30,
        import_stale_retention_minutes=30,
    )

    cleanup_import_storage(settings, session)

    assert task_directory.exists()


def test_cleanup_import_storage_removes_orphan_directory(tmp_path: Path) -> None:
    from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
    from app.core.config import Settings

    session = _create_session()
    task_directory = tmp_path / "import-batch-orphan"
    task_directory.mkdir(parents=True)
    source_file_path = task_directory / "demo.xlsx"
    source_file_path.write_bytes(b"demo")
    stale_timestamp = (datetime.now() - timedelta(minutes=31)).timestamp()
    source_file_path.touch()
    task_directory.touch()
    Path(source_file_path).touch()

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        import_storage_dir=tmp_path,
        import_success_retention_minutes=10,
        import_failed_retention_minutes=30,
        import_stale_retention_minutes=30,
    )

    import os

    os.utime(task_directory, (stale_timestamp, stale_timestamp))
    os.utime(source_file_path, (stale_timestamp, stale_timestamp))

    cleanup_import_storage(settings, session)

    assert not task_directory.exists()
