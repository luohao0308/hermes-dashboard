# Phase 7: Multi-Agent 实时监控

> hermes_free + openai-agents-python + MiniMax Multi-Agent
> 创建时间: 2026-04-26

## 目标

1. hermes_free 后端新增多 Agent 协作系统，监控 + 协作
2. 前端实时看到每个 Agent 的状态（idle/running/error/handoff）
3. 能在前端创建 Agent、查看 Agent 日志
4. MiniMax API 复用

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                        │
│  AgentPanel: 卡片列表 | 状态灯 | 日志流 | 创建表单           │
└────────────────────────┬────────────────────────────────────┘
                         │ SSE (:8000/sse)
                         │
┌────────────────────────▼────────────────────────────────────┐
│              hermes_free Backend (FastAPI)                   │
│                                                             │
│  ┌──────────────┐   ┌──────────────────────────────────┐   │
│  │ SSE Bridge   │   │ AgentOrchestrator                 │   │
│  │ (已有)       │   │  ├── triage_agent (路由/分发)     │   │
│  └──────────────┘   │  ├── monitor_agent (Hermès监控)   │   │
│                     │  ├── analyst_agent (数据分析)     │   │
│                     │  └── executor_agent (任务执行)    │   │
│                     └──────────────────────────────────┘   │
│                                    │                        │
│                                    │ handoffs               │
└────────────────────────────────────▼─────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  MiniMax API        │
              │  OpenAIChatCompletionsModel │
              │  MiniMax-M2.7-highspeed  │
              └─────────────────────┘

Hermès Agent (:9119) ──────────────────────────────────────►│
                                                             │ 定期拉取
                                                             │ sessions
```

### 核心组件

```
backend/
├── main.py                  # 新增端点
├── sse_manager.py            # (已有)
├── config.py                # (已有)
├── agent/
│   ├── __init__.py
│   ├── client.py            # MiniMax client 初始化
│   ├── orchestrator.py      # AgentOrchestrator 类
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── triage.py       # TriageAgent
│   │   ├── monitor.py      # MonitorAgent (Hermès 状态监控)
│   │   ├── analyst.py      # AnalystAgent (会话分析)
│   │   └── executor.py     # ExecutorAgent (任务执行)
│   └── models.py           # Pydantic 状态模型
```

## 前端新增

```
frontend/src/
├── components/
│   ├── AgentPanel.vue      # Agent 总览面板 (新增)
│   ├── AgentCard.vue       # 单个 Agent 卡片 (新增)
│   └── AgentLogViewer.vue  # Agent 日志查看器 (新增)
└── views/
    └── (App.vue 已有路由，新增 nav item)
```

## Multi-Agent 协作流程

### Agent 职责

| Agent | 角色 | 触发条件 | 能力 |
|-------|------|----------|------|
| `TriageAgent` | 入口/路由器 | 用户查询进入 | 理解意图，分发给对应 Agent |
| `MonitorAgent` | Hermès 监控 | 定时 30s | 检测 session 异常、任务卡住、错误率 |
| `AnalystAgent` | 会话分析 | 被 Triage 调用 | 分析 session 详情、token 消耗、失败原因 |
| `ExecutorAgent` | 任务执行 | 被 Triage 调用 | 执行单次任务调用、写文件等 |

### Handoff 流程

```
用户: "上一个 session 为何失败？"
       │
       ▼
TriageAgent (意图分类)
       │
       ├── "查询状态" → MonitorAgent
       │                    │
       │                    └── 分析 Hermès sessions API
       │
       └── "分析原因" → AnalystAgent
                            │
                            └── 调用 Hermès /api/sessions/{id} 详情
```

### SSE 推送事件

后端 → 前端 SSE 事件类型：

| Event | Payload | 说明 |
|-------|---------|------|
| `agent_created` | `{id, name, status}` | 新 Agent 创建 |
| `agent_status` | `{id, name, status, message}` | 状态变更 |
| `agent_handoff` | `{from_id, to_id, reason}` | Agent 间切换 |
| `agent_output` | `{id, delta}` | 流式输出片段 |
| `agent_error` | `{id, error}` | 错误信息 |
| `agent_complete` | `{id, result}` | 任务完成 |
| `hermes_alert` | `{level, message, session_id}` | Hermès 异常告警 |

## API 设计

### 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/agents` | 列出所有 Agent 状态 |
| `POST` | `/api/agents` | 创建新 Agent |
| `GET` | `/api/agents/{id}` | 获取单个 Agent 详情 |
| `DELETE` | `/api/agents/{id}` | 删除 Agent |
| `POST` | `/api/agents/{id}/invoke` | 触发 Agent 执行 |
| `GET` | `/api/agents/events` | SSE 流，订阅所有 Agent 事件 |
| `GET` | `/health` | (已有) 健康检查 |

### 创建 Agent 请求

```json
POST /api/agents
{
  "name": "my-agent",
  "role": "analyst",       // triage | monitor | analyst | executor
  "instructions": "你是一个...",
  "handoffs": ["monitor", "analyst"]
}
```

### 创建 Agent 响应

```json
{
  "id": "agent_abc123",
  "name": "my-agent",
  "role": "analyst",
  "status": "idle",
  "created_at": "2026-04-26T10:00:00Z"
}
```

## 前端页面设计

### AgentPanel 布局

```
┌─────────────────────────────────────────────────────┐
│ 🤖 Agent 工作台                         [+ 新建 Agent] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ 🟢 Triage   │ │ 🟡 Monitor  │ │ 🔵 Analyst  │  │
│  │   idle      │ │  running    │ │   idle      │  │
│  │  32 events  │ │  15 events  │ │   8 events  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  📋 MonitorAgent 日志                        │  │
│  │  ──────────────────────────────────────────   │  │
│  │  [10:00:01] ✅ Hermès connected               │  │
│  │  [10:00:31] ℹ️  检查 session abc123...        │  │
│  │  [10:00:32] ⚠️  Session abc123 idle > 5min    │  │
│  │  [10:00:33] → handoff to AnalystAgent         │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  💬 发送消息到 TriageAgent:                   │  │
│  │  ┌──────────────────────────────────┐ [发送] │  │
│  │  │                                  │        │  │
│  │  └──────────────────────────────────┘        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 文件变更清单

### Backend

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/agent/__init__.py` | 新增 | 模块入口 |
| `backend/agent/client.py` | 新增 | MiniMax AsyncOpenAI 客户端 |
| `backend/agent/models.py` | 新增 | Pydantic 状态模型 |
| `backend/agent/orchestrator.py` | 新增 | AgentOrchestrator 生命周期管理 |
| `backend/agent/agents/triage.py` | 新增 | TriageAgent |
| `backend/agent/agents/monitor.py` | 新增 | MonitorAgent |
| `backend/agent/agents/analyst.py` | 新增 | AnalystAgent |
| `backend/agent/agents/executor.py` | 新增 | ExecutorAgent |
| `backend/main.py` | 修改 | 新增 `/api/agents` 端点，集成到 SSE manager |
| `backend/requirements.txt` | 修改 | 新增 `openai-agents-python` |

### Frontend

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/AgentPanel.vue` | 新增 | Agent 总览面板 |
| `frontend/src/components/AgentCard.vue` | 新增 | Agent 卡片组件 |
| `frontend/src/components/AgentLogViewer.vue` | 新增 | 日志查看器 |
| `frontend/src/App.vue` | 修改 | 新增 nav item: "Agent 工作台" |
| `frontend/src/components/Sidebar.vue` | 修改 | 可能已有 nav |

## 实施步骤

### Task 1: 后端基础 - Agent 客户端 + 模型
- [ ] `backend/agent/client.py` — MiniMax AsyncOpenAI 客户端（复用 config 中的 API key）
- [ ] `backend/agent/models.py` — `AgentState`, `AgentEvent` Pydantic 模型
- [ ] `backend/agent/__init__.py`
- [ ] 验证: `python -c "from backend.agent import client; print('OK')"`

### Task 2: TriageAgent + 流式 SSE
- [ ] `backend/agent/agents/triage.py` — TriageAgent 实现
- [ ] `backend/agent/agents/__init__.py`
- [ ] 新增 `POST /api/agents/invoke` 端点
- [ ] 新增 `GET /api/agents/events` SSE 端点
- [ ] 验证: SSE 连接成功收到 agent_created 事件

### Task 3: MonitorAgent + Hermès 集成
- [ ] `backend/agent/agents/monitor.py` — MonitorAgent
- [ ] MonitorAgent 定时拉取 Hermès `/api/sessions`
- [ ] 异常检测: session idle > 5min、end_reason 非正常
- [ ] 新增 `hermes_alert` SSE 事件
- [ ] 验证: 30s 内收到 hermes_alert

### Task 4: AnalystAgent + ExecutorAgent
- [ ] `backend/agent/agents/analyst.py` — AnalystAgent
- [ ] `backend/agent/agents/executor.py` — ExecutorAgent
- [ ] `backend/agent/orchestrator.py` — AgentOrchestrator 统一管理
- [ ] handoff 流程测试: Triage → Monitor → Analyst

### Task 5: 前端 AgentPanel
- [ ] `frontend/src/components/AgentCard.vue` — 卡片（状态灯 + 事件计数）
- [ ] `frontend/src/components/AgentLogViewer.vue` — 日志流组件
- [ ] `frontend/src/components/AgentPanel.vue` — 总览 + 创建表单
- [ ] App.vue 添加 "Agent 工作台" nav
- [ ] 前端 SSE 订阅 `agent_status`, `hermes_alert` 事件
- [ ] 验证: `npm run build` 通过

### Task 6: 端到端测试
- [ ] 创建 Agent → 看到卡片出现
- [ ] 发送消息 → 看到 SSE 流式响应
- [ ] MonitorAgent 触发告警 → 前端收到 hermes_alert
- [ ] handoff 发生 → 前端看到 agent_handoff 事件
- [ ] CI: `npm run test:unit` + `flake8 backend` + `python -m py_compile`

## 技术要点

### MiniMax 流式事件处理

```python
# backend/agent/client.py
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

model = OpenAIChatCompletionsModel(
    model="MiniMax-M2.7-highspeed",
    openai_client=AsyncOpenAI(
        api_key=settings.minimax_api_key,
        base_url="https://api.minimax.chat/v1",
        http_client=httpx.AsyncClient(proxies=...)  # 如需要代理
    )
)

# Runner 流式
result = Runner.run_streamed(agent, user_input)
async for event in result.stream_events():
    if event.type == "run_item_stream_event":
        if event.name == "tool_called":
            await sse_manager.broadcast("agent_tool", {...})
        elif event.name == "message_output_created":
            text = event.item.content.first_text
            await sse_manager.broadcast("agent_output", {"delta": text})
    elif event.type == "agent_updated_stream_event":
        await sse_manager.broadcast("agent_handoff", {
            "from_id": current_agent_id,
            "to_id": event.new_agent.name,
        })
```

### SSE 事件广播

SSE manager 已有 `broadcast(event_type, data)` 方法，直接复用：

```python
# 在 Agent 运行时
await sse_manager.broadcast("agent_status", {
    "id": agent_id,
    "name": agent.name,
    "status": "running",
})
```

### 依赖安装到 conda hermes310

```bash
source ~/opt/anaconda3/etc/profile.d/conda.sh
conda activate hermes310
pip install openai-agents-python
# 注意: openai-agents-python 不在 PyPI，需用:
pip install git+https://github.com/openai/openai-agents-python
```

## 风险与备选

| 风险 | 缓解 |
|------|------|
| openai-agents-python 不在 PyPI | 用 `git+https://` 安装 |
| SOCKS 代理拦截请求 | `http_client=httpx.AsyncClient(proxies=...)` |
| MiniMax 不支持 streaming 回调 | 用 `Runner.run_streamed` + `stream_events` |
| Hermès Agent 本身已有监控 | MonitorAgent 只做补充告警，不重复 Hermès 已有功能 |
| 多 Agent 状态管理复杂 | 用 `AgentOrchestrator` 统一管理生命周期 |

## 验证标准

- [ ] 后端: `curl localhost:8000/health` 正常
- [ ] 后端: `curl localhost:8000/api/agents` 返回 Agent 列表
- [ ] 后端: `curl localhost:8000/api/agents/events` 能建立 SSE 连接
- [ ] 前端: 打开 Agent 工作台，看到 4 个 Agent 卡片（初始 idle）
- [ ] 前端: 发送消息，5s 内看到 SSE 流式响应
- [ ] 前端: MonitorAgent 检测到异常 session，前端收到 `hermes_alert` 事件并展示
- [ ] CI: `npm run test:unit` 通过，`flake8 backend` 无错误
