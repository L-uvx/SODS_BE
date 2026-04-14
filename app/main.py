from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.polygon_obstacle import router as polygon_obstacle_router
from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
from app.core import runtime
from app.core.config import Settings
from app.db.session import SessionLocal
from app.tasks.polygon_obstacle_import import run_import_task

app = FastAPI()
app.state.settings = Settings.from_env()
app.state.dispatch_import_task = run_import_task.delay
runtime.settings = app.state.settings
runtime.dispatch_import_task = app.state.dispatch_import_task
app.include_router(polygon_obstacle_router)


@app.on_event("startup")
def cleanup_stale_import_storage() -> None:
    session = SessionLocal()
    try:
        cleanup_import_storage(app.state.settings, session)
    except SQLAlchemyError:
        # Startup cleanup is best-effort and must not block app boot.
        return
    finally:
        session.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
