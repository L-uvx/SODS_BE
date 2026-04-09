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

## Docker Compose

### 启动依赖服务和 API

```bash
docker compose up --build api postgres redis
```

API 启动后可通过 `http://localhost:8000/health` 访问健康检查接口。
