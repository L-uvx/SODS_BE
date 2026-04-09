# SODS_BE

空间障碍检测系统后端。

## Local Development

### Install dependencies

```bash
uv sync --dev
```

### Run the API

```bash
uv run uvicorn app.main:app --reload
```

### Run tests

```bash
uv run pytest -v
```

## Docker Compose

### Start dependencies and API

```bash
docker compose up api postgres redis
```

API will be available at `http://localhost:8000/health`.
