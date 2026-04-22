from app.application.polygon_obstacle_import import PolygonObstacleImportService
from app.core.celery_app import celery_app
from app.db.session import SessionLocal


# 执行分析任务的 Celery 入口。
@celery_app.task(name="polygon_obstacle_analysis.run_analysis_task")
def run_analysis_task(analysis_task_id: str) -> None:
    session = SessionLocal()
    try:
        service = PolygonObstacleImportService(session)
        service.run_analysis_task(analysis_task_id)
    finally:
        session.close()
