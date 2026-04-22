import os
from dataclasses import dataclass
from dataclasses import field
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
    export_storage_dir: Path = field(default_factory=lambda: Path("var/exports"))
    export_success_retention_minutes: int = 10
    export_failed_retention_minutes: int = 30
    export_stale_retention_minutes: int = 30

    # 从环境变量加载应用配置。
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
            export_storage_dir=Path(os.getenv("EXPORT_STORAGE_DIR", "var/exports")),
            export_success_retention_minutes=int(
                os.getenv("EXPORT_SUCCESS_RETENTION_MINUTES", "10")
            ),
            export_failed_retention_minutes=int(
                os.getenv("EXPORT_FAILED_RETENTION_MINUTES", "30")
            ),
            export_stale_retention_minutes=int(
                os.getenv("EXPORT_STALE_RETENTION_MINUTES", "30")
            ),
        )
