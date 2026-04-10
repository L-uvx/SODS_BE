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
