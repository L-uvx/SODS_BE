import os
import tempfile
from pathlib import Path

from app.core.config import Settings


def test_settings_use_default_values(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("IMPORT_STORAGE_DIR", raising=False)
    monkeypatch.delenv("IMPORT_SUCCESS_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("IMPORT_FAILED_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("IMPORT_STALE_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("EXPORT_STORAGE_DIR", raising=False)
    monkeypatch.delenv("EXPORT_SUCCESS_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("EXPORT_FAILED_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("EXPORT_STALE_RETENTION_MINUTES", raising=False)
    monkeypatch.delenv("FRONTEND_DIST_DIR", raising=False)

    settings = Settings.from_env()

    assert settings.app_env == "development"
    assert (
        settings.database_url
        == "postgresql+psycopg://postgres:postgres@localhost:5432/sods_be"
    )
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.import_storage_dir.as_posix() == "var/imports"
    assert settings.import_success_retention_minutes == 10
    assert settings.import_failed_retention_minutes == 30
    assert settings.import_stale_retention_minutes == 30
    assert settings.export_storage_dir.as_posix() == "var/exports"
    assert settings.export_success_retention_minutes == 10
    assert settings.export_failed_retention_minutes == 30
    assert settings.export_stale_retention_minutes == 30
    assert settings.frontend_dist_dir == Path("../frontend/dist")


def test_settings_allow_environment_overrides(monkeypatch) -> None:
    import_dir = os.path.join(tempfile.gettempdir(), "imports")
    export_dir = os.path.join(tempfile.gettempdir(), "exports")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/app")
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("IMPORT_STORAGE_DIR", import_dir)
    monkeypatch.setenv("IMPORT_SUCCESS_RETENTION_MINUTES", "3")
    monkeypatch.setenv("IMPORT_FAILED_RETENTION_MINUTES", "7")
    monkeypatch.setenv("IMPORT_STALE_RETENTION_MINUTES", "11")
    monkeypatch.setenv("EXPORT_STORAGE_DIR", export_dir)
    monkeypatch.setenv("EXPORT_SUCCESS_RETENTION_MINUTES", "13")
    monkeypatch.setenv("EXPORT_FAILED_RETENTION_MINUTES", "17")
    monkeypatch.setenv("EXPORT_STALE_RETENTION_MINUTES", "19")
    monkeypatch.setenv("FRONTEND_DIST_DIR", "/opt/frontend/dist")

    settings = Settings.from_env()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/app"
    assert settings.redis_url == "redis://cache:6379/1"
    assert settings.import_storage_dir == Path(import_dir)
    assert settings.import_success_retention_minutes == 3
    assert settings.import_failed_retention_minutes == 7
    assert settings.import_stale_retention_minutes == 11
    assert settings.export_storage_dir == Path(export_dir)
    assert settings.export_success_retention_minutes == 13
    assert settings.export_failed_retention_minutes == 17
    assert settings.export_stale_retention_minutes == 19
    assert settings.frontend_dist_dir == Path("/opt/frontend/dist")
