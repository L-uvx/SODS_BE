# SODS_BE

空间障碍检测系统后端。

## Local Development

### 安装依赖

```bash
uv sync --dev
```

### 启动 API

```bash
uv run uvicorn app.main:app --reload
```

### 运行测试

```bash
uv run pytest -v
```

## 配置

可选环境变量：

- `APP_ENV`
- `DATABASE_URL`
- `REDIS_URL`

当前项目已接入基于 `SQLAlchemy` 的最小数据库基础设施，并继续使用 `DATABASE_URL` 作为数据库连接配置入口。

当前模型基座已包含：

- `projects`
- `obstacles`

其中 `obstacles.geom` 按 PostGIS `MultiPolygon (EPSG:4326)` 设计，`raw_payload` 用于保留原始导入数据快照。

## 数据库迁移

当前项目已接入最小 `Alembic` 迁移体系，可使用以下命令：

```bash
uv run alembic revision -m "message"
uv run alembic upgrade head
```

## Docker Compose

### 启动依赖服务和 API

```bash
docker compose up --build api postgres redis
```

API 启动后可通过 `http://localhost:8000/health` 访问健康检查接口。
