# Hermès Dashboard 架构文档

## 系统架构图

![Architecture Diagram](./architecture-diagram.html)

## 技术栈

### 后端
- **FastAPI** - Python Web 框架
- **SSE (Server-Sent Events)** - 实时事件流
- **uvicorn** - ASGI 服务器
- **pytest** - 自动化测试

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 快速构建工具
- **TailwindCSS** - 原子化 CSS
- **Naive UI** - Vue 3 组件库

## 系统组件

### 1. Hermès Agent
- 运行的 CLI 实例
- 通过 ACP 协议发送事件
- 事件类型：任务更新、日志输出等

### 2. Bridge Server
- FastAPI 应用
- 端口：8000
- 核心端点：`/sse`
- 负责接收 Hermès 事件并广播给所有连接的客户端

### 3. Vue Frontend
- 任务状态面板 (TaskPanel.vue)
- 实时日志流 (LogStream.vue)
- 历史任务列表 (HistoryList.vue)

### 4. SSE Connection Manager
- 管理所有 SSE 连接
- 提供广播功能
- 支持多客户端同时连接

## 数据流

```
Hermès Agent
    │
    │ ACP Protocol / Events
    ▼
Bridge Server (FastAPI)
    │
    │ SSE Stream
    ▼
Vue Frontend
    │
    │ HTTP
    ▼
Web Browser
```

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
        ├── feature/backend-sse
        ├── feature/frontend-scaffold
        ├── feature/task-panel
        ├── feature/log-stream
        └── feature/history-list
```

## 文件结构

```
hermes_free/
├── README.md
├── backend/
│   ├── main.py          # FastAPI 应用
│   ├── sse_manager.py   # SSE 连接管理
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── components/
│   │       ├── TaskPanel.vue
│   │       ├── LogStream.vue
│   │       └── HistoryList.vue
│   └── ...
├── tests/
│   ├── backend/
│   │   └── test_sse.py
│   └── frontend/
│       └── ...
└── docs/
    └── architecture-diagram.html
```

## 相关笔记

- [[🖥️ Hermès Dashboard 项目]]
- [[📋 TODO]]

---

*最后更新：2026-04-25*
