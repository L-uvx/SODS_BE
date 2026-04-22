from app.application.polygon_obstacle_import import PolygonObstacleImportService
from app.core.celery_app import celery_app
from app.db.session import SessionLocal


# 执行导出任务的 Celery 入口。
@celery_app.task(name="polygon_obstacle_export.run_export_task")
def run_export_task(export_task_id: str) -> None:
    session = SessionLocal()
    try:
        service = PolygonObstacleImportService(session)
        service.run_export_task(export_task_id)
    finally:
        session.close()
