# openai-agents-python 集成计划

> 基于 hermes_free 现状分析，2026-04-26

## 现状分析

### 当前架构
```
[Hermès Agent v0.10.0] ←(localhost:9119)─ [hermes_free FastAPI 桥接] ←(SSE)─ [Vue Frontend]
                                    port 8000                          port 5173
```

- **Hermès Agent**：已在运行（v0.10.0），有活跃 session (MiniMax-M2.7-highspeed)，有 tool calling (66 calls/session)
- **hermes_free**：纯桥接层，把 Hermès API 数据代理到前端 SSE 流，只做展示，不做 AI 逻辑
- **Frontend**：Vue 3 展示 Hermès 的任务/日志/历史

### 关键问题
**Hermès Agent 本身已经是 AI Agent**，有完整的多轮对话、工具调用能力。openai-agents-python 能做什么额外的事？

---

## 选项 1：给 hermes_free 增加 Agentic 监控能力

**思路**：hermes_free 不再只是透传数据，而是启动一个 AI Agent 主动分析 Hermès 的行为，给出洞察、建议、自动操作。

### 架构
```
[Hermès Agent] ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
                                                   ↓
[hermes_free FastAPI]                              │
  ├── SSE Bridge (已有)                            │
  └── AI Monitor Agent (新增)                      │
        ├── 读取 Hermès sessions API              │
        ├── 分析活跃任务状态                       │
        ├── 检测异常 (任务卡住、错误率高等)       │
        └── 通过 SSE 推送告警/建议到前端          │
                                                   │
                              [Vue Frontend] ◄────┘
                              (告警面板 / AI 建议)
```

### Agent 能做什么
| 能力 | 说明 |
|------|------|
| 异常检测 | 任务长时间无进展、连续错误、自动中断 |
| 性能洞察 | session token 消耗分析、cache 命中率 |
| 自动化操作 | 发现任务失败后自动重试、向 Hermès 发命令 |
| 自然语言查询 | 用户问"上一个任务为什么失败了"，Agent 分析日志回答 |

### 技术实现
```python
# hermes_free/backend/agent/monitor.py
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
import asyncio

client = AsyncOpenAI(
    api_key=os.environ["MINIMAX_API_KEY"],
    base_url="https://api.minimax.chat/v1"
)
model = OpenAIChatCompletionsModel(
    model="MiniMax-M2.7-highspeed",
    openai_client=client
)

monitor_agent = Agent(
    name="Hermes Monitor",
    instructions="""你是 Hermès Agent 的监控助手。
    每当收到任务状态更新时，判断是否需要告警。
    如果任务失败，分析可能原因并给出建议。
    只在有意义的时候才输出，不要每次都说话。""",
    model=model,
)
```

### 依赖
- `openai-agents-python`（已装在系统 Python 3.10）
- MiniMax API Key（已有）
- 新增 `/api/agent/query` 端点接收用户自然语言查询

### 风险
- Hermès Agent 本身已有监控能力，可能重复
- 增加 API 调用成本（每次分析都走 MiniMax）
- Agent 可能产生幻觉建议

---

## 选项 2：新建 AI 任务 Pipeline

**思路**：hermes_free 不再只是监控，而是成为一个**任务下发入口**。用户在前端创建任务 → openai-agents-python Agent 执行 → 结果通过 SSE 推送 → 前端展示。

### 架构
```
[Vue Frontend]                    [hermes_free FastAPI]
  │                                      │
  │  1. 用户提交任务                      │
  ├─────────────────────────────────────►│
  │                                      │  2. 创建 Agent Task
  │                                      │     (openai-agents-python)
  │                                      │
  │                                      │  3. Agent 执行中...
  │◄── 4. SSE 实时进度/日志 ──────────────┤
  │                                      │
  │                                      │  5. 完成后写入 Hermès sessions
  │                                      ↓
  │                              [Hermès Agent API]
```

### Agent 能做什么
| 能力 | 说明 |
|------|------|
| 代码助手 | 写代码、debug、重构（类似 Code Interpreter） |
| 任务分解 | 用户给目标，Agent 自动拆解成子任务 |
| 多步骤自动化 | "帮我分析这个 GitHub repo" → clone → 阅读 → 总结 |
| 对话式任务 | 用户和 Agent 来回对话直到任务完成 |

### 技术实现
```python
# hermes_free/backend/agent/pipeline.py
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["MINIMAX_API_KEY"],
    base_url="https://api.minimax.chat/v1"
)
model = OpenAIChatCompletionsModel(
    model="MiniMax-M2.7-highspeed",
    openai_client=client
)

task_agent = Agent(
    name="Task Agent",
    instructions="你是任务执行助手。接收用户目标，执行工具调用，返回结果。",
    model=model,
    tools=[...],  # 文件读写、shell 命令等
)

# SSE 进度推送
async def run_task_streaming(user_input: str):
    result = Runner.run(task_agent, user_input, stream=True)
    async for event in result.stream_events():
        if event.type == "text_delta":
            await sse_manager.broadcast("agent_output", {"delta": event.data})
        elif event.type == "tool_call":
            await sse_manager.broadcast("agent_tool", {"tool": event.data})
```

### 新增 API 端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agent/run` | POST | 下发 AI 任务，返回 task_id |
| `/api/agent/{task_id}/events` | SSE | 任务执行过程的流式事件 |
| `/api/agent/{task_id}/result` | GET | 获取任务最终结果 |

### 依赖
- openai-agents-python + MiniMax
- 可能需要增加文件上传能力（Agent 要读写文件）
- sandbox 环境（安全执行 shell 命令）

### 风险
- Agent 执行任意 shell 命令有安全风险，需要 sandbox
- 与 Hermès Agent 功能重叠
- 长时间运行任务需要状态持久化

---

## 方案对比

| | 选项1: Monitor Agent | 选项2: Task Pipeline |
|---|---|---|
| **复杂度** | 中（新增一个后台 Agent） | 高（流式执行、sandbox、状态管理） |
| **新增依赖** | 少 | 多（sandbox、文件管理） |
| **与现有系统关系** | 补充 Hermès | 可能替代部分 Hermès 功能 |
| **实用性** | 监控告警，马上有用 | 功能强大但实现周期长 |
| **风险** | 低 | 高（安全、稳定性） |
| **推荐度** | ★★★★☆ | ★★★☆☆ |

---

## 推荐路径

**先做选项 1（Monitor Agent）**：
1. 创建一个 `backend/agent/monitor.py`
2. 新增 `/api/agent/query` 端点
3. Monitor Agent 监听 Hermès 状态，异常时告警
4. 通过 SSE 推送到前端新增的 "AI 洞察" 面板

**后续再考虑选项 2**，如果选项 1 验证有效且确实需要任务执行能力。

---

## 下一步行动

1. 用户确认走选项 1 还是选项 2
2. 确认 MiniMax API Key 是否可用（已在 Hermès 中使用）
3. 创建 Phase 7 计划文档
4. 开分支实施
