from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.application.polygon_obstacle_import import PolygonObstacleImportService


# 执行导入任务的 Celery 入口。
@celery_app.task(name="polygon_obstacle_import.run_import_task")
def run_import_task(import_task_id: str) -> None:
    session = SessionLocal()
    try:
        service = PolygonObstacleImportService(session)
        service.run_import_task(import_task_id)
    finally:
        session.close()
