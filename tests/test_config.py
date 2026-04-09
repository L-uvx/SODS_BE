from app.core.config import Settings


def test_settings_use_default_values(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = Settings.from_env()

    assert settings.app_env == "development"
    assert (
        settings.database_url
        == "postgresql+psycopg://postgres:postgres@localhost:5432/sods_be"
    )
    assert settings.redis_url == "redis://localhost:6379/0"


def test_settings_allow_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/app")
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")

    settings = Settings.from_env()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/app"
    assert settings.redis_url == "redis://cache:6379/1"
