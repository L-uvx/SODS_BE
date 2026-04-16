# SODS_BE

空间障碍检测系统后端。

## 当前能力

1. `GET /health` 健康检查
2. 多边形障碍物导入与导入结果查询
3. 候选机场查询与 `bootstrap` 初始化接口
4. analysis 任务创建、状态查询与结果查询
5. export 任务创建、状态查询、结果查询与报告下载
6. import / analysis / export 三段 Celery 异步任务执行

## 快速启动

优先使用 Docker Compose：

```bash
docker compose up --build api worker postgres redis
```

健康检查：`http://127.0.0.1:8000/health`

预期返回：

```json
{"status":"ok"}
```

日志：

```bash
docker compose logs -f api worker
```

停止：

```bash
docker compose down
```

## 本地开发

当前项目优先在 WSL 中开发，不要从 Windows 侧直接对 `\\wsl.localhost\...` 项目目录运行 `uv`。

项目目录：

```bash
cd /home/lo1yer/Project/SODS_BE
```

推荐 `uv`：

```bash
/home/lo1yer/anaconda3/bin/uv
```

安装依赖：

```bash
/home/lo1yer/anaconda3/bin/uv sync --dev
```

启动 API：

```bash
/home/lo1yer/anaconda3/bin/uv run uvicorn app.main:app --reload
```

启动 worker：

```bash
/home/lo1yer/anaconda3/bin/uv run celery -A app.core.celery_app:celery_app worker --loglevel=info
```

## 测试与迁移

全部测试：

```bash
/home/lo1yer/anaconda3/bin/uv run pytest -v
```

核心回归：

```bash
/home/lo1yer/anaconda3/bin/uv run pytest tests/test_polygon_obstacle_export_api.py tests/test_app_import.py tests/test_config.py tests/test_models.py tests/test_migrations.py tests/test_polygon_obstacle_excel_parser.py tests/test_polygon_obstacle_targets.py tests/test_polygon_obstacle_import_api.py tests/test_polygon_obstacle_import_cleanup.py -v
```

迁移：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic upgrade head
```

新建 revision：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic revision -m "message"
```

离线 SQL：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic upgrade head --sql
```

## 环境变量

1. `APP_ENV`
2. `DATABASE_URL`
3. `REDIS_URL`
4. `IMPORT_STORAGE_DIR`
5. `IMPORT_SUCCESS_RETENTION_MINUTES`
6. `IMPORT_FAILED_RETENTION_MINUTES`
7. `IMPORT_STALE_RETENTION_MINUTES`
8. `EXPORT_STORAGE_DIR`
9. `EXPORT_SUCCESS_RETENTION_MINUTES`
10. `EXPORT_FAILED_RETENTION_MINUTES`
11. `EXPORT_STALE_RETENTION_MINUTES`

## 关键注意事项

1. 当前 `obstacles.geom` 的正式口径是 `MultiPolygon / 4326`，不要回退成 `Point` 或其他占位类型。
2. 当前 import、analysis 与 export 都已完成 Celery 异步化，不要误判为同步请求内执行。
3. 当前 worker 任务注册依赖 `app/core/celery_app.py` 对任务模块的显式导入，不要删除该导入。
4. 当前容器内虚拟环境固定在 `/opt/venv`，不要改回 `/app/.venv`。
5. 当前 Docker 镜像已切换为非 root 用户运行，避免再改回 root。
6. 当前 `docker-compose.yml` 中 worker 已直接使用 `/opt/venv/bin/celery` 启动，不要改回 `uv run celery`。
7. 当前 `stations` 只是机场内部基础数据，不属于当前 `GET /polygon-obstacle/import/{taskId}/targets` 返回范围。
8. 当前导出结果查询接口返回 `downloadUrl`，实际文件下载走独立的 `GET /polygon-obstacle/exports/{exportTaskId}/download`。
9. 当前 export 文件已接入与 import 一致的启动补偿清理：成功任务保留 10 分钟，失败任务保留 30 分钟，`pending/running` 与孤儿目录超过 30 分钟清理。
