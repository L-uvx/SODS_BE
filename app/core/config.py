import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    import_storage_dir: Path
    import_success_retention_minutes: int
    import_failed_retention_minutes: int
    import_stale_retention_minutes: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/sods_be",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            import_storage_dir=Path(os.getenv("IMPORT_STORAGE_DIR", "var/imports")),
            import_success_retention_minutes=int(
                os.getenv("IMPORT_SUCCESS_RETENTION_MINUTES", "10")
            ),
            import_failed_retention_minutes=int(
                os.getenv("IMPORT_FAILED_RETENTION_MINUTES", "30")
            ),
            import_stale_retention_minutes=int(
                os.getenv("IMPORT_STALE_RETENTION_MINUTES", "30")
            ),
        )
