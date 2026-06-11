# SODS_BE

空间障碍检测系统后端。

## 快速启动

优先使用 Docker Compose：

```bash
docker compose up --build api worker postgres redis
```

健康检查：`http://127.0.0.1:8000/health`，预期返回 `{"status":"ok"}`。

```bash
docker compose logs -f api worker   # 查看日志
docker compose down                 # 停止
```

## 数据库迁移

```bash
uv run alembic upgrade head        # 执行迁移
uv run alembic revision -m "xxx"   # 新建 revision
uv run alembic upgrade head --sql  # 生成离线 SQL
```

## 环境变量

可通过 `.env` 文件或 `docker-compose.yml` 配置，各变量均有默认值，本地开发通常无需额外设置。Docker 部署已在 `docker-compose.yml` 中预置好了必填项。

`app/core/config.py` 中有默认配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_ENV` | `development` | 运行环境 |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/sods_be` | 数据库连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `IMPORT_STORAGE_DIR` | `var/imports` | 导入文件存储目录 |
| `IMPORT_SUCCESS_RETENTION_MINUTES` | `10` | 导入成功保留分钟数 |
| `IMPORT_FAILED_RETENTION_MINUTES` | `30` | 导入失败保留分钟数 |
| `IMPORT_STALE_RETENTION_MINUTES` | `30` | 导入残留清理分钟数 |
| `EXPORT_STORAGE_DIR` | `var/exports` | 导出文件存储目录 |
| `EXPORT_SUCCESS_RETENTION_MINUTES` | `10` | 导出成功保留分钟数 |
| `EXPORT_FAILED_RETENTION_MINUTES` | `30` | 导出失败保留分钟数 |
| `EXPORT_STALE_RETENTION_MINUTES` | `30` | 导出残留清理分钟数 |
| `FRONTEND_DIST_DIR` | `../../frontend/dist` | 前端静态文件目录（便携部署时通过环境变量覆盖为绝对路径） |

## Windows 便携部署

项目支持脱离 Docker/WSL 在 Windows 上运行，详见 `../SODS_Portable/README.md`。

Windows 下需注意：`localhost` 可能在 psycopg 中先尝试 IPv6 导致连接挂死。若遇到数据库连接超时，将 `DATABASE_URL` 中的 `@localhost` 改为 `@127.0.0.1`。此外 Python `mimetypes` 在 Windows 上可能将 `.js` 映射为 `text/plain` 导致前端模块加载失败，`app/main.py` 启动时已通过 `mimetypes.add_type` 修复。

## 许可证管理

项目内部工具位于 `tools/` 目录：

- `tools/license_gen.py` — 许可证签发工具（供应商使用，不交付客户）
- `tools/private_key.pem` — RSA 私钥（不提交 git，不随发布包分发）

客户许可证文件为 `data/license.json`（位于 `SODS_Portable/data/` 目录下）。
