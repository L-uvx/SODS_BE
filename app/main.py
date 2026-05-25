from contextlib import asynccontextmanager
import mimetypes

# 修复 Windows 环境下 StaticFiles 对 .js/.mjs 的 MIME 类型识别问题
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.data_management import router as data_management_router
from app.api.polygon_obstacle import point_router, router as polygon_obstacle_router
from app.application.polygon_obstacle_import_cleanup import cleanup_export_storage
from app.application.polygon_obstacle_import_cleanup import cleanup_import_storage
from app.core import runtime
from app.core.config import Settings
from app.db.session import SessionLocal
from app.tasks.polygon_obstacle_analysis import run_analysis_task
from app.tasks.polygon_obstacle_export import run_export_task
from app.tasks.polygon_obstacle_import import run_import_task


# 启动时清理过期的导入和导出目录。
def cleanup_stale_import_storage() -> None:
    session = SessionLocal()
    try:
        cleanup_import_storage(app.state.settings, session)
        cleanup_export_storage(app.state.settings, session)
    except SQLAlchemyError:
        # Startup cleanup is best-effort and must not block app boot.
        return
    finally:
        session.close()


# 管理应用启动和关闭阶段的生命周期。
@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_stale_import_storage()
    yield


app = FastAPI(lifespan=lifespan)
app.state.settings = Settings.from_env()
app.state.dispatch_import_task = run_import_task.delay
app.state.dispatch_analysis_task = run_analysis_task.delay
app.state.dispatch_export_task = run_export_task.delay
runtime.settings = app.state.settings
runtime.dispatch_import_task = app.state.dispatch_import_task
runtime.dispatch_analysis_task = app.state.dispatch_analysis_task
runtime.dispatch_export_task = app.state.dispatch_export_task
app.include_router(polygon_obstacle_router)
app.include_router(point_router)
app.include_router(data_management_router)


# 返回服务健康状态。
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# 便携部署：如果前端 dist 目录存在，挂载静态文件并提供 SPA 路由回退
_frontend_dir = app.state.settings.frontend_dist_dir
if _frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="frontend",
    )
