# 生产部署指南

## 前置条件

- Python 3.9+
- Node.js 20+
- PostgreSQL 14+
- Docker（可选）

## 部署步骤

### 1. 环境配置

```bash
cp .env.example .env
```

必须设置的环境变量：

| 变量 | 描述 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接字符串 |
| `ENVIRONMENT` | 设为 `production` |
| `ENCRYPTION_KEY` | Fernet 密钥（`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`） |

### 2. 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 3. 启动服务

```bash
./start.sh
```

该脚本会：
- 启动后端 FastAPI 服务（默认端口 8000）
- 启动前端 Vite 开发服务器（默认端口 5173）

### 4. 生产环境建议

- 使用 Gunicorn + Uvicorn workers 运行 FastAPI
- 使用 Nginx 反向代理前端静态文件
- 配置 HTTPS
- 设置 PostgreSQL 连接池
- 配置日志收集（结构化 JSON 日志）

## 健康检查

```bash
curl http://localhost:8000/health
```

返回数据库连接状态、Worker 状态、调度器状态等。

## 监控

- `/health` — 健康状态矩阵
- `/api/metrics` — 运行指标（总运行数、失败数、待审批数等）
- 结构化日志包含 correlation ID

## 备份与恢复

参见 [BACKUP_RESTORE_RUNBOOK.md](BACKUP_RESTORE_RUNBOOK.md)
