# Hermès Dashboard 架构文档

## 系统架构图

![Architecture Diagram](./architecture-diagram.html)

## 技术栈

### 后端
- **FastAPI** - Python Web 框架
- **SSE (Server-Sent Events)** - 实时事件流
- **uvicorn** - ASGI 服务器
- **pytest** - 自动化测试
- **httpx** - 异步 HTTP 客户端（代理 Hermes Dashboard API）

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 快速构建工具
- **TailwindCSS** - 原子化 CSS
- **TypeScript** - 类型安全

## 系统组件

### 1. Hermès Agent
- 运行的 CLI 实例
- 包含内置 Dashboard（端口 9119）
- 提供 REST API：`/api/status`、`/api/sessions`、`/api/tasks`、`/api/logs` 等

### 2. Bridge Server（后端代理）
- FastAPI 应用，端口：8000
- 代理 Hermes Dashboard API（:9119），解决 CORS 问题
- SSE 端点 `/sse` 转发 Hermès 实时事件
- 关键端点：
  - `GET /api/status` - 代理 `/api/status`
  - `GET /api/tasks` - 代理 `/api/tasks`
  - `GET /api/tasks/{id}` - 代理 `/api/tasks/{id}`（先验证 session 存在）
  - `GET /api/logs` - 代理 `/api/logs`
  - `GET /sse` - SSE 事件流

### 3. Vue Frontend
- 端口：5173
- 通过后端代理获取 Hermes 数据
- 组件：
  - TaskPanel.vue - 当前任务状态
  - LogStream.vue - 实时日志流
  - HistoryList.vue - 历史任务列表

## 数据流

```
Hermès Agent (Dashboard :9119)
    │
    │ REST API (HTTP)
    ▼
Bridge Server (FastAPI :8000)  ←── 代理模式，消除 CORS
    │
    │ SSE Stream / HTTP API
    ▼
Vue Frontend (:5173)
    │
    │ HTTP
    ▼
Web Browser
```

### 代理模式说明
- 前端直接请求后端（:8000）
- 后端转发请求到 Hermes Dashboard（:9119）
- 解决浏览器 CORS 跨域限制
- 后端自动从 Dashboard HTML 页面提取 session token

## GitHub 工作流

```
Engineer ──▶ 创建分支 ──▶ 实现功能 ──▶ 提交 PR
                                    │
                ┌───────────────────┘
                ▼
              QA 执行测试
                │
                ├── 通过 ──▶ Lead 审核 ──▶ Merge
                │
                └── 失败 ──▶ 打回 Engineer 修复
```

## 分支策略

```
main (保护分支)
    │
    └── feature/* (开发分支)
```

当前活跃分支：
- `main` - 生产就绪
- `feature/hermes-proxy` - 后端代理模式（已合并）

## 文件结构

```
hermes_free/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── architecture-diagram.html
├── backend/
│   ├── main.py          # FastAPI 代理应用
│   ├── sse_manager.py   # SSE 连接管理
│   ├── config.py        # 配置管理
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── components/
│   │       ├── TaskPanel.vue
│   │       ├── LogStream.vue
│   │       └── HistoryList.vue
│   ├── tests/           # Vitest 组件测试
│   │   ├── test_task_panel.spec.ts
│   │   ├── test_log_stream.spec.ts
│   │   └── test_history_list.spec.ts
│   └── vitest.config.ts
└── tests/
    └── backend/
        └── test_sse.py  # Pytest 后端测试
```

## 测试覆盖

### 后端测试 (pytest)
- `tests/backend/test_sse.py` - SSE 端点、API 代理、错误处理
- 运行方式：`cd backend && pytest` 或 `pytest`（项目根目录）

### 前端测试 (Vitest)
- `frontend/tests/*.spec.ts` - Vue 组件渲染、props、事件
- 运行方式：`cd frontend && npx vitest run`

---

*最后更新：2026-04-25 - Phase 3.1 完成，代理模式架构*
