import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.application.polygon_obstacle_import import PolygonObstacleImportService

logger = logging.getLogger(__name__)


# 执行导入任务的 Celery 入口。
@celery_app.task(name="polygon_obstacle_import.run_import_task")
def run_import_task(import_task_id: str) -> None:
    session = SessionLocal()
    try:
        service = PolygonObstacleImportService(session)
        service.run_import_task(import_task_id)
    except Exception:
        logger.exception(
            "celery import task %s safety net fired", import_task_id
        )
        try:
            from app.repository.import_batch_repository import ImportBatchRepository

            repo = ImportBatchRepository(session)
            repo.mark_import_batch_failed(
                import_task_id, "import task encountered an unexpected error"
            )
        except Exception:
            pass
    finally:
        session.close()
