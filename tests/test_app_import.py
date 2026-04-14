import importlib
import sys

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
    sys.modules.pop("app.tasks.polygon_obstacle_analysis", None)
    sys.modules.pop("app.tasks.polygon_obstacle_import", None)
    sys.modules.pop("app.core.celery_app", None)

    celery_module = importlib.import_module("app.core.celery_app")
    celery_app = celery_module.celery_app

    assert "polygon_obstacle_import.run_import_task" in celery_app.tasks
    assert "polygon_obstacle_analysis.run_analysis_task" in celery_app.tasks
