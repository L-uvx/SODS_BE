# SODS_BE

空间障碍检测系统后端。

当前仓库已经具备以下核心能力：

1. `GET /health` 健康检查
2. 多边形障碍物导入
3. 导入结果查询与候选机场查询
4. bootstrap 初始化接口
5. analysis 最小闭环接口
6. import 环节 Celery 异步任务执行

## 1. Docker 部署与运行

如果你只是想把服务跑起来，优先使用 Docker Compose。

### 前台启动

```bash
docker compose up --build api worker postgres redis
```

适用场景：

1. 本地联调
2. 需要直接在终端看日志输出
3. 需要快速观察 `api` 和 `worker` 的启动状态

### 后台启动

```bash
docker compose up -d --build api worker postgres redis
```

适用场景：

1. 服务需要持续在后台运行
2. 希望另开终端执行接口调试或数据库操作

查看日志：

```bash
docker compose logs -f api worker
```

查看全部服务日志：

```bash
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

### 健康检查

服务启动后，可访问：

```text
http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 2. 本地开发

当前项目优先在 WSL 中开发。

不要从 Windows 侧直接对 `\\wsl.localhost\...` 项目目录运行 `uv`，否则容易把 Windows 解释器和 WSL 的 `.venv/` 混用，导致虚拟环境损坏或依赖安装异常。

### 进入项目目录

```bash
cd /home/lo1yer/Project/SODS_BE
```

### 安装依赖

当前环境推荐使用的 `uv` 路径：

```bash
/home/lo1yer/anaconda3/bin/uv
```

安装开发依赖：

```bash
/home/lo1yer/anaconda3/bin/uv sync --dev
```

### 启动 API

```bash
/home/lo1yer/anaconda3/bin/uv run uvicorn app.main:app --reload
```

### 启动 Celery Worker

```bash
/home/lo1yer/anaconda3/bin/uv run celery -A app.core.celery_app:celery_app worker --loglevel=info
```

说明：

1. 本地开发时，`api` 和 `worker` 需要分别启动
2. 当前 import 已经是异步任务，只有启动 worker 后导入任务才会真正被消费执行

### 运行测试

运行全部测试：

```bash
/home/lo1yer/anaconda3/bin/uv run pytest -v
```

运行当前核心回归测试：

```bash
/home/lo1yer/anaconda3/bin/uv run pytest tests/test_app_import.py tests/test_config.py tests/test_models.py tests/test_migrations.py tests/test_polygon_obstacle_excel_parser.py tests/test_polygon_obstacle_targets.py tests/test_polygon_obstacle_import_api.py tests/test_polygon_obstacle_import_cleanup.py -v
```

## 3. 环境变量

当前主要环境变量如下：

1. `APP_ENV`
2. `DATABASE_URL`
3. `REDIS_URL`
4. `IMPORT_STORAGE_DIR`
5. `IMPORT_SUCCESS_RETENTION_MINUTES`
6. `IMPORT_FAILED_RETENTION_MINUTES`
7. `IMPORT_STALE_RETENTION_MINUTES`

说明：

1. `DATABASE_URL` 用于数据库连接
2. `REDIS_URL` 用于 Celery broker 和 result backend
3. `IMPORT_STORAGE_DIR` 用于保存导入原始文件
4. 当前导入源文件默认会短时保留并由启动补偿清理机制处理

## 4. 数据库迁移

当前项目已接入 `Alembic`。

创建迁移：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic revision -m "message"
```

执行迁移：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic upgrade head
```

查看离线 SQL：

```bash
/home/lo1yer/anaconda3/bin/uv run alembic upgrade head --sql
```

## 5. 当前服务结构

当前 Docker Compose 包含以下服务：

1. `api`：FastAPI 应用
2. `worker`：Celery worker，负责异步导入任务
3. `postgres`：PostgreSQL + PostGIS
4. `redis`：Celery broker / result backend

## 6. 常用命令

Docker 前台启动：

```bash
docker compose up --build api worker postgres redis
```

Docker 后台启动：

```bash
docker compose up -d --build api worker postgres redis
```

查看日志：

```bash
docker compose logs -f api worker
```

本地启动 API：

```bash
/home/lo1yer/anaconda3/bin/uv run uvicorn app.main:app --reload
```

本地启动 worker：

```bash
/home/lo1yer/anaconda3/bin/uv run celery -A app.core.celery_app:celery_app worker --loglevel=info
```

运行测试：

```bash
/home/lo1yer/anaconda3/bin/uv run pytest -v
```

## 7. 开发注意事项

1. 当前 `obstacles.geom` 的正式口径是 `MultiPolygon / 4326`，不要回退成 `Point` 或其他占位类型。
2. 当前 import 已完成 Celery 异步化，不要再把 `POST /polygon-obstacle/import` 误判为同步解析接口。
3. 当前 worker 任务注册依赖 `app/core/celery_app.py` 对任务模块的显式导入，不要删除该导入。
4. 当前容器内虚拟环境固定在 `/opt/venv`，不要改回 `/app/.venv`。
5. 当前 Docker 镜像已切换为非 root 用户运行，避免再改回 root。
6. 当前 `docker-compose.yml` 中 worker 已直接使用 `/opt/venv/bin/celery` 启动，不要改回 `uv run celery`。
7. 当前 `stations` 只是机场内部基础数据，不属于当前 `GET /polygon-obstacle/import/{taskId}/targets` 返回范围。
