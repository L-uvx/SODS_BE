import importlib
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base


def test_app_main_imports_without_circular_model_error() -> None:
    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    assert module.app is not None


def test_model_registry_populates_base_metadata() -> None:
    importlib.import_module("app.db.models")

    assert "projects" in Base.metadata.tables
    assert "import_batches" in Base.metadata.tables
    assert "obstacles" in Base.metadata.tables


def test_celery_registers_polygon_obstacle_import_task() -> None:
    sys.modules.pop("app.main", None)
    sys.modules.pop("app.tasks.polygon_obstacle_export", None)
    sys.modules.pop("app.tasks.polygon_obstacle_analysis", None)
    sys.modules.pop("app.tasks.polygon_obstacle_import", None)
    sys.modules.pop("app.core.celery_app", None)

    celery_module = importlib.import_module("app.core.celery_app")
    celery_app = celery_module.celery_app

    assert "polygon_obstacle_import.run_import_task" in celery_app.tasks
    assert "polygon_obstacle_analysis.run_analysis_task" in celery_app.tasks
    assert "polygon_obstacle_export.run_export_task" in celery_app.tasks


def test_app_startup_triggers_export_cleanup(monkeypatch, tmp_path: Path) -> None:
    import app.main as app_main

    calls: list[Path] = []

    def _fake_cleanup(settings, session) -> None:
        calls.append(settings.export_storage_dir)

    monkeypatch.setattr(app_main, "cleanup_export_storage", _fake_cleanup)
    monkeypatch.setattr(
        app_main,
        "cleanup_import_storage",
        lambda settings, session: None,
    )
    app_main.app.state.settings = app_main.app.state.settings.__class__(
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

    app_main.cleanup_stale_import_storage()

    assert calls == [tmp_path / "exports"]


def test_app_startup_ignores_sqlalchemy_error_from_export_cleanup(
    monkeypatch,
) -> None:
    import app.main as app_main

    monkeypatch.setattr(
        app_main,
        "cleanup_import_storage",
        lambda settings, session: None,
    )

    def _raise_cleanup(settings, session) -> None:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(app_main, "cleanup_export_storage", _raise_cleanup)

    app_main.cleanup_stale_import_storage()
