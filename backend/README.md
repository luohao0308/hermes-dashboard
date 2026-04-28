# Hermès Bridge Service

FastAPI + SSE 后端服务，用于 Hermès 监控平台。

## 功能特性

- **SSE 实时通信**: 基于 Server-Sent Events 的实时消息推送
- **连接管理**: 跟踪管理所有 SSE 客户端连接
- **事件广播**: 向所有连接客户端广播消息
- **心跳保活**: 自动心跳机制保持连接活跃
- **任务管理**: 内置示例任务管理 API
- **CORS 支持**: 跨域请求支持

## 快速开始

### 环境要求

- Python 3.10+（推荐 3.11，与 Dockerfile 保持一致）

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 使用 Docker

```bash
docker build -t hermes-bridge .
docker run -p 8000:8000 hermes-bridge
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/sse` | GET | SSE 实时事件流 |
| `/health` | GET | 健康检查 |
| `/connections` | GET | 列出所有活动连接 |
| `/connections/{client_id}` | GET | 获取特定连接信息 |
| `/broadcast` | POST | 向所有客户端广播消息 |
| `/tasks` | GET | 列出所有任务 |
| `/tasks/{task_id}` | GET | 获取特定任务 |
| `/tasks/{task_id}/broadcast` | POST | 广播任务更新 |

## SSE 连接示例

```bash
# 连接 SSE 端点
curl -N http://localhost:8000/sse

# 带查询参数连接
curl -N "http://localhost:8000/sse?token=xxx"
```

## 广播消息示例

```bash
curl -X POST "http://localhost:8000/broadcast?event_type=alert&message=Test%20alert"
```

## 事件类型

服务会自动生成以下事件类型:

- `connected`: 连接建立时发送
- `heartbeat`: 心跳保活 (每30秒)
- `task_update`: 任务更新 (每5秒)
- `system_status`: 系统状态 (每3秒)

## 配置

可通过环境变量或 `.env` 文件配置:

```env
HOST=0.0.0.0
PORT=8000
HEARTBEAT_INTERVAL=30
MAX_CONNECTIONS=1000
EVENT_GENERATION_INTERVAL=1
```
