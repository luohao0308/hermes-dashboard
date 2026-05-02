# Multi-Agent Orchestration Patterns

> 多Agent编排模式：从理论到 hermes_free 落地
> 生成日期: 2026-04-30

---

## 一、编排模式总览

2026 年主流的 6 种多 Agent 编排模式：

```
┌─────────────────────────────────────────────────┐
│           Multi-Agent Orchestration              │
├──────────┬──────────┬──────────┬────────────────┤
│Sequential│Concurrent│Supervisor│  Hierarchical  │
├──────────┼──────────┼──────────┼────────────────┤
│ Peer2Peer│  Swarm   │  Mesh    │ Event-Driven   │
└──────────┴──────────┴──────────┴────────────────┘
```

### 1. Sequential Pipeline（顺序流水线）

```
Agent A -> Agent B -> Agent C -> Result
```

- **适用**: 有明确依赖的任务链（如：分析 -> 生成 -> 审查）
- **hermes_free 现状**: Review Pipeline 已实现（fetch diff -> 多模型审查 -> 共识 -> 发布）
- **改进点**: 增加条件路由，失败时跳转到修复 Agent

### 2. Concurrent / Fan-out Fan-in（并发扇出汇聚）

```
         +-> Agent A -+
Input -->+-> Agent B -+-> Aggregator -> Result
         +-> Agent C -+
```

- **适用**: 同一输入需要多角度分析
- **hermes_free 现状**: asyncio.gather 并行多 Provider 审查已实现
- **改进点**: 增加动态扇出数量（根据任务复杂度自动决定并行度）

### 3. Supervisor / Orchestrator-Worker（监督者模式）

```
                  +-> Worker A (coding)
Orchestrator -->--+-> Worker B (testing)
                  +-> Worker C (review)
                        |
                  Orchestrator aggregates
```

- **适用**: 任务可拆分为独立子任务
- **hermes_free 现状**: orchestrator.py 接近此模式，但 Worker 间无隔离
- **改进点**: Worker 应有独立 context window、独立重试策略

### 4. Hierarchical（层级模式）

```
Master Orchestrator
+-- Team Lead A
|   +-- Worker A1
|   +-- Worker A2
+-- Team Lead B
    +-- Worker B1
    +-- Worker B2
```

- **适用**: 大型复杂项目，需要多级委派
- **建议**: hermes_free 未来扩展方向

### 5. Peer-to-Peer（对等模式）

```
Agent A <--> Agent B
  ^             ^
  v             v
Agent C <--> Agent D
```

- **适用**: Agent 间需要协商和辩论
- **案例**: AutoGen/AG2 的 GroupChat，多 Agent 轮流发言
- **注意**: 4 Agent x 5 轮 = 20 次 LLM 调用，成本高

### 6. Event-Driven（事件驱动模式）

```
Event Bus
+-- Agent A subscribes: [task.created]
+-- Agent B subscribes: [review.completed]
+-- Agent C subscribes: [alert.triggered]
```

- **适用**: 松耦合、可扩展的系统
- **hermes_free 现状**: SSE manager 已有广播能力，但不是真正的事件总线
- **改进点**: 引入发布-订阅事件总线

---

## 二、框架对比（2026）

| 框架 | 编排模型 | 状态持久化 | 模型依赖 | 最佳场景 |
|------|----------|-----------|---------|---------|
| LangGraph | 有向图 + 条件边 | 内置 checkpoint + 时间旅行 | 模型无关 | 复杂有状态工作流 |
| CrewAI | 角色化 crew | 任务输出顺序传递 | 模型无关 | 快速原型、角色化任务 |
| AutoGen/AG2 | GroupChat 对话 | 会话历史（内存） | 模型无关 | 研究、代码审查、辩论 |
| OpenAI SDK | Handoff 转交 | 上下文变量（临时） | OpenAI only | OpenAI 生态 |
| Claude Agent SDK | 工具链 + subagent | MCP 服务器 | Claude only | Anthropic 生态、安全优先 |
| Google ADK | 层级 Agent 树 | Session state + 可插拔后端 | 优先 Gemini | Google Cloud |

---

## 三、hermes_free 推荐编排方案

### 短期（1-2 周）：强化 Supervisor 模式

```python
class SupervisorOrchestrator:
    """监督者编排器 - 管理 Worker Agent 的生命周期"""

    async def execute(self, task: Task) -> Result:
        # 1. 任务拆解
        subtasks = await self.decompose(task)

        # 2. 依赖分析，构建 DAG
        dag = self.build_dag(subtasks)

        # 3. 按拓扑序执行，无依赖的任务并行
        results = {}
        for level in dag.topological_levels():
            level_results = await asyncio.gather(*[
                self.dispatch_worker(subtask)
                for subtask in level
            ])
            results.update(level_results)

        # 4. 聚合结果
        return await self.aggregate(results)
```

### 中期（1-2 月）：引入事件驱动

```python
class EventBus:
    """进程内事件总线"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event):
        for handler in self._subscribers[event.type]:
            await handler(event)
```

### 长期（3-6 月）：DAG 编排 + 持久化

```python
class DAGEngine:
    """DAG 任务编排引擎"""

    async def run(self, dag: TaskDAG):
        pending = dag.ready_tasks()  # 无依赖的任务

        while pending:
            # 并发执行
            results = await asyncio.gather(*[
                self.execute_with_retry(task) for task in pending
            ])

            # 更新依赖图，找出新就绪的任务
            for task, result in zip(pending, results):
                dag.mark_complete(task.id, result)

            pending = dag.ready_tasks()
```

---

## 四、Handoff 协议设计

Agent 间传递的结构化交接包：

```python
@dataclass(frozen=True)
class HandoffPackage:
    goal: str                    # 目标陈述
    completed_steps: list[str]   # 已完成步骤
    relevant_findings: list[str] # 相关发现
    open_questions: list[str]    # 未解决问题
    constraints: list[str]       # 约束条件
    recommended_next: str        # 建议下一步
    context_tokens: int          # 上下文 token 数
```

---

## 五、参考资源

- Azure AI Agent Design Patterns
- Openlayer Multi-Agent Guide (March 2026)
- Anthropic Harness Design for Long-Running Apps
- Deloitte Agent Orchestration 2026 Predictions
- Digital Applied Multi-Agent Workflow Guide
