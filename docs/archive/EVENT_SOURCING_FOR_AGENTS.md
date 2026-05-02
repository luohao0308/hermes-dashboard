# Event Sourcing & CQRS for Agent Systems

> 事件溯源与CQRS在Agent系统中的应用
> 生成日期: 2026-04-30

---

## 一、为什么 Agent 系统需要事件溯源

### 传统 CRUD 的问题

```
Agent State (mutable) --> Overwritten on each update
  - 无法回答"为什么做出这个决策"
  - 无法回放失败场景
  - 无法审计 Agent 行为
  - 状态丢失后无法恢复
```

### Event Sourcing 的优势

```
Event Log (append-only):
  [TaskCreated] -> [AgentAssigned] -> [ToolCalled] -> [LLMRequested] ->
  [LLMResponded] -> [ToolCompleted] -> [ReviewFailed] -> [RetryTriggered] ->
  [ToolCalled] -> [LLMRequested] -> [LLMResponded] -> [TaskCompleted]

  Current State = replay(events)
```

**对 Agent 系统的独特价值**:
1. **完整审计链**: 每个决策、每次 LLM 调用、每个工具调用都有记录
2. **时间旅行**: 重建任意时刻的 Agent 状态
3. **确定性回放**: 重现失败场景进行调试
4. **爆炸半径控制**: 通过合约限制单个 Agent 的影响范围

---

## 二、ESAA 模式（Event Sourcing for Autonomous Agents）

来源: arxiv 2602.23193

### 核心思想

Agent 不直接"写状态"，而是发射**意图**和**建议的 diff**，由确定性编排器验证并应用。

```
Agent                    Orchestrator              Event Store
  |                          |                         |
  |-- emit intent ---------->|                         |
  |   (proposed diff)        |-- validate invariant -->|
  |                          |-- apply if valid ------->|
  |                          |                         |-- append event
  |<-- result ---------------|                         |
```

### 与传统 Agent 的对比

| 维度 | 传统 Agent | ESAA Agent |
|------|-----------|------------|
| 状态存储 | 可变快照 | 不可变事件日志 |
| 决策追踪 | 无或手动日志 | 原生事件链 |
| 回放能力 | 不支持 | 确定性回放 |
| 爆炸半径 | 无边界 | 合约约束 |
| 读写耦合 | 紧耦合 | CQRS 分离 |

---

## 三、CQRS 在 Agent 系统中的应用

### Ask vs Act 分离

```
Query (Ask):                    Command (Act):
  - 读取知识库                     - 创建 PR
  - 搜索文档                      - 修改文件
  - 分析代码                      - 发送消息
  - 获取状态                      - 部署代码

  路径: 多源读取（缓存、DB、API）    路径: 写入权威系统
  约束: 可容忍短暂不一致             约束: 需要人工确认
```

### Agent CQRS 架构

```
┌─────────────────────────────────────────┐
│              Agent Layer                │
│  ┌─────────┐    ┌─────────────────┐    │
│  │  Query   │    │    Command      │    │
│  │ Handler  │    │    Handler      │    │
│  └────┬─────┘    └────────┬────────┘    │
│       │                   │             │
│  ┌────▼─────┐    ┌────────▼────────┐    │
│  │  Read    │    │   Write Model   │    │
│  │  Model   │    │  (Event Store)  │    │
│  │(Projection)│  │                 │    │
│  └──────────┘    └─────────────────┘    │
└─────────────────────────────────────────┘
```

**关键约束**: Agent 读取的数据可能有短暂延迟（最终一致性），对于需要做不可逆决策的 Agent，必须从写模型读取最新数据。

---

## 四、hermes_free 落地方案

### 4.1 Event Store 设计

```python
# backend/events/event_store.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import sqlite3

class EventType(Enum):
    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Agent actions
    AGENT_SPAWNED = "agent.spawned"
    AGENT_HANDOFF = "agent.handoff"
    AGENT_COMPLETED = "agent.completed"

    # LLM interactions
    LLM_REQUESTED = "llm.requested"
    LLM_RESPONDED = "llm.responded"
    LLM_FAILED = "llm.failed"

    # Tool calls
    TOOL_INVOKED = "tool.invoked"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Guardrails
    GUARDRAIL_TRIGGERED = "guardrail.triggered"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"

@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: EventType
    aggregate_id: str       # task_id or session_id
    timestamp: datetime
    data: dict              # immutable event payload
    metadata: dict          # agent_id, model, tokens, cost

class EventStore:
    """SQLite-backed event store with append-only semantics"""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT NOT NULL,
                sequence INTEGER AUTOINCREMENT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_aggregate "
            "ON events(aggregate_id, sequence)"
        )
        self.conn.commit()

    def append(self, event: Event) -> None:
        """Append event - NEVER update or delete"""
        self.conn.execute(
            "INSERT INTO events (event_id, event_type, aggregate_id, "
            "timestamp, data, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.event_type.value, event.aggregate_id,
             event.timestamp.isoformat(), json.dumps(event.data),
             json.dumps(event.metadata))
        )
        self.conn.commit()

    def get_events(self, aggregate_id: str) -> list[Event]:
        """Replay all events for an aggregate"""
        cursor = self.conn.execute(
            "SELECT * FROM events WHERE aggregate_id = ? ORDER BY sequence",
            (aggregate_id,)
        )
        return [self._row_to_event(row) for row in cursor]
```

### 4.2 Projection（读模型）

```python
# backend/events/projections.py
class TaskProjection:
    """从事件重建当前任务状态"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def get_task_state(self, task_id: str) -> dict:
        """从事件流重建任务状态"""
        events = self.event_store.get_events(task_id)
        state = {"task_id": task_id, "status": "unknown", "history": []}

        for event in events:
            state = self._apply_event(state, event)

        return state

    def _apply_event(self, state: dict, event: Event) -> dict:
        """事件 -> 状态转换（纯函数，不可变）"""
        match event.event_type:
            case EventType.TASK_CREATED:
                return {**state, "status": "created", "created_at": event.timestamp,
                        "spec": event.data.get("spec")}
            case EventType.TASK_ASSIGNED:
                return {**state, "status": "assigned",
                        "agent_id": event.data.get("agent_id")}
            case EventType.TASK_COMPLETED:
                return {**state, "status": "completed",
                        "result": event.data.get("result"),
                        "completed_at": event.timestamp}
            case _:
                return {**state, "history": [*state["history"], event]}
```

### 4.3 Agent Event Emitter

```python
# backend/events/emitter.py
import uuid
from datetime import datetime

class AgentEventEmitter:
    """Agent 事件发射器 - 封装事件创建和存储"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def emit_task_created(self, task_id: str, spec: str):
        self.event_store.append(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_CREATED,
            aggregate_id=task_id,
            timestamp=datetime.utcnow(),
            data={"spec": spec},
            metadata={}
        ))

    def emit_llm_call(self, aggregate_id: str, agent_id: str,
                      model: str, input_tokens: int, output_tokens: int,
                      cost_usd: float, latency_ms: int):
        self.event_store.append(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.LLM_RESPONDED,
            aggregate_id=aggregate_id,
            timestamp=datetime.utcnow(),
            data={"model": model, "input_tokens": input_tokens,
                  "output_tokens": output_tokens},
            metadata={"agent_id": agent_id, "cost_usd": cost_usd,
                      "latency_ms": latency_ms}
        ))
```

---

## 五、事件版本管理

```python
class EventUpcaster:
    """事件版本升级器 - 处理 schema 演变"""

    UPGRADERS = {
        ("task.created", 1, 2): lambda data: {**data, "priority": "normal"},
        ("llm.requested", 1, 2): lambda data: {**data, "stream": False},
    }

    def upcast(self, event_type: str, version: int, data: dict) -> dict:
        target_version = self._latest_version(event_type)
        while version < target_version:
            upgrader = self.UPGRADERS.get((event_type, version, version + 1))
            if upgrader:
                data = upgrader(data)
            version += 1
        return data
```

---

## 六、参考资源

- ESAA: Event Sourcing for Autonomous Agents (arxiv 2602.23193)
- CQRS for AI Agents (Tacnode Blog)
- Ask vs Act: Applying CQRS Principles to AI Agents (Ryan Spletzer)
- Event Sourcing and CQRS Implementation Guide (youngju.dev)
- Mia-Platform: Understanding Event Sourcing and CQRS Pattern
