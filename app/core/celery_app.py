from celery import Celery

from app.core.config import Settings


settings = Settings.from_env()

celery_app = Celery(
    "sods_be",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import task modules explicitly so workers started with
# `-A app.core.celery_app:celery_app` always register them.
import app.tasks.polygon_obstacle_import  # noqa: F401,E402
import app.tasks.polygon_obstacle_analysis  # noqa: F401,E402
