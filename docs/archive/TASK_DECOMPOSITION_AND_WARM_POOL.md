# Task Decomposition & Warm Pool Optimization

> 任务拆解架构与连接池/预热优化方案
> 生成日期: 2026-04-30

---

## 一、任务拆解架构

### 1.1 三阶段流水线模型

```
Phase 1: Task Decomposition (任务拆解)
  Planner Agent (只读)
  输入: 产品规格 / 用户需求
  输出: 结构化任务列表 + 依赖关系

Phase 2: Worker Loop (工作循环)
  Graph Executor
  按依赖图调度，并发执行无依赖任务
  每个 Worker Agent 只处理一个子任务

Phase 3: Review & Fix (审查修复)
  Reviewer Agent 审计完成的工作
  如有问题，Debugger Agent 修复
```

### 1.2 任务数据结构

```python
class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    description: str
    agent_role: str
    tools: list[str]
    dependencies: list[str] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 3600
    context_files: list[str] = field(default_factory=list)
```

### 1.3 DAG 编排引擎

```python
class TaskDAG:
    def __init__(self):
        self.tasks: dict[str, TaskSpec] = {}
        self.edges: dict[str, list[str]] = defaultdict(list)
        self.completed: set[str] = set()
        self.failed: set[str] = set()

    def ready_tasks(self) -> list[TaskSpec]:
        ready = []
        for task_id, task in self.tasks.items():
            if task_id in self.completed or task_id in self.failed:
                continue
            deps_met = all(d in self.completed for d in task.dependencies)
            if deps_met:
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority.value)

    def topological_levels(self) -> list[list[TaskSpec]]:
        levels = []
        remaining = set(self.tasks.keys())
        while remaining:
            level = [t for t in remaining
                     if all(d in self.completed for d in self.tasks[t].dependencies)]
            if not level:
                break
            levels.append([self.tasks[t] for t in level])
            for t in level:
                remaining.discard(t)
                self.completed.add(t)
        return levels
```

### 1.4 Planner Agent

```python
class PlannerAgent:
    PLANNER_PROMPT = """You are a task decomposition specialist.
Given a requirement, decompose it into structured tasks with:
1. task_id, 2. title, 3. agent_role, 4. dependencies, 5. estimated_tokens
Output as JSON array. Do NOT execute any tasks."""

    async def decompose(self, requirement: str) -> TaskDAG:
        response = await self.llm.chat(
            system=self.PLANNER_PROMPT,
            user=requirement,
            response_format={"type": "json_object"}
        )
        tasks = self.parse_tasks(response)
        dag = TaskDAG()
        for task in tasks:
            dag.add_task(task)
        return dag
```

### 1.5 Worker Loop

```python
class WorkerLoop:
    async def execute(self, dag: TaskDAG) -> dict:
        results = {}
        while True:
            ready = dag.ready_tasks()
            if not ready:
                break
            level_results = await asyncio.gather(*[
                self._execute_task(task, results) for task in ready
            ])
            for task, result in zip(ready, level_results):
                if result.success:
                    dag.mark_complete(task.task_id)
                    results[task.task_id] = result
                else:
                    dag.mark_failed(task.task_id)
        return results
```

---

## 二、Warm Pool 与连接优化

### 2.1 连接池设计

```python
class LLMConnectionPool:
    def __init__(self):
        self._clients: dict[str, httpx.AsyncClient] = {}

    async def get_client(self, provider: str, base_url: str) -> httpx.AsyncClient:
        if provider not in self._clients:
            self._clients[provider] = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(connect=10.0, read=300.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                http2=True
            )
        return self._clients[provider]
```

### 2.2 Provider 预热

```python
class ProviderWarmPool:
    async def warmup_all(self):
        providers = self.registry.list_providers()
        results = await asyncio.gather(*[
            self._warmup_provider(p) for p in providers
        ])
        for provider, success in zip(providers, results):
            self._ready[provider.name] = success

    async def _warmup_provider(self, provider) -> bool:
        await self.pool.get_client(provider.name, provider.base_url)
        health = await provider.health_check()
        if health:
            await provider.list_models()
        return health
```

### 2.3 Agent 实例池

```python
class AgentPool:
    def __init__(self, config_loader, pool_size: int = 3):
        self._pools: dict[str, asyncio.Queue] = {}

    async def initialize(self):
        for agent_cfg in self.config_loader.load_agents():
            pool = asyncio.Queue(maxsize=self.pool_size)
            for _ in range(self.pool_size):
                await pool.put(self._create_agent(agent_cfg))
            self._pools[agent_cfg.role] = pool

    @asynccontextmanager
    async def acquire(self, role: str):
        agent = await self._pools[role].get()
        try:
            yield agent
        finally:
            await self._pools[role].put(agent)
```

### 2.4 LLM 响应缓存

```python
class LLMResponseCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    async def get_or_call(self, model, messages, caller, **kwargs):
        key = self._make_key(model, messages, **kwargs)
        if key in self._cache:
            result, ts = self._cache[key]
            if datetime.utcnow() - ts < self.ttl:
                return result
        result = await caller(model=model, messages=messages, **kwargs)
        self._cache[key] = (result, datetime.utcnow())
        return result
```

---

## 三、上下文窗口优化

### Token 预算管理

```python
class TokenBudget:
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.available = max_tokens - 4096  # 预留输出

    def allocate(self, sections: dict[str, int]) -> dict[str, int]:
        priority = ["system_prompt", "tools", "context", "history"]
        allocated, remaining = {}, self.available
        for section in priority:
            actual = min(sections.get(section, 0), remaining)
            allocated[section] = actual
            remaining -= actual
        return allocated
```

### Subagent 摘要压缩

```python
class SubagentCondenser:
    async def condense(self, raw_output: str, max_tokens: int = 2000) -> str:
        if self.count_tokens(raw_output) <= max_tokens:
            return raw_output
        return await self.llm.chat(
            system="Summarize in under 500 words. Preserve key findings.",
            user=raw_output, max_tokens=max_tokens
        )
```

---

## 四、完整任务执行流程

```
用户请求
    |
    v
[Planner Agent] --> TaskDAG
    |
    v
[Worker Loop]
    |-- Level 0: [Task A]
    |-- Level 1: [Task B] [Task C] (并行)
    |               |          |
    |         [Agent Pool] [Agent Pool]
    |           (warm)      (warm)
    |               |          |
    |         [LLM Conn]  [LLM Conn]
    |           (reuse)     (reuse)
    |-- Level 2: [Task D] (依赖 B, C)
    |
    v
[Reviewer Agent] --> 通过? --> 完成
                     |
                     否 --> [Debugger] --> 回到 Worker Loop
```

---

## 五、参考资源

- WarmServe: GPU Prewarming for Multi-LLM Serving (arxiv 2512.09472)
- AWS SageMaker Managed Warm Pools
- Harness Engineering: Why Coding Agents Need Infrastructure
- HTTP Connection Pooling Best Practices (Microsoft)
- Pancake: Hierarchical Memory for Multi-Agent LLM Serving (arxiv 2602.21477)
