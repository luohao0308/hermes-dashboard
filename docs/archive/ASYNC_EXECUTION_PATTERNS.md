# Async Execution & Long-Running Task Patterns

> 异步执行模式与长时间任务处理方案
> 生成日期: 2026-04-30

---

## 一、LLM 作为高延迟微服务

LLM 调用的独特属性（与传统 DB 查询对比）:

| 属性 | 数据库查询 | LLM 调用 |
|------|-----------|----------|
| 延迟 | 5-50ms | 5,000-15,000ms |
| 倍数 | 1x | 100-3000x |
| 超时风险 | 低 | 高 |
| 流式输出 | 不需要 | 强烈推荐 |
| 成本 | 固定 | 按 token 计费 |

结论: 不能用传统的同步请求-响应模式处理 LLM 调用。

---

## 二、异步执行模式对比

### 模式 1: FastAPI BackgroundTasks（最轻量）

```python
@app.post("/review")
async def start_review(pr_url: str, background_tasks: BackgroundTasks):
    task_id = create_task(pr_url)
    background_tasks.add_task(run_review, task_id)
    return {"task_id": task_id, "status": "processing"}
```

| 特性 | 支持情况 |
|------|---------|
| 设置复杂度 | 极低 |
| 可观测性 | 无 |
| 可靠性 | 任务可能丢失 |
| 重试机制 | 无 |
| 并发控制 | 无 |
| 扩展性 | 绑定 web 服务器 |

适用: 轻量级 fire-and-forget（发送通知、更新缓存）
不适用: 长时间运行的 Agent 任务

### 模式 2: asyncio.create_task（进程内并发）

```python
class TaskManager:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    async def submit(self, task_id: str, coro):
        task = asyncio.create_task(coro)
        self._tasks[task_id] = task
        task.add_done_callback(lambda t: self._on_complete(task_id, t))
```

hermes_free 现状: 当前使用此模式

### 模式 3: ARQ + Redis（推荐轻量方案）

```python
from arq import create_pool
from arq.connections import RedisSettings

async def run_agent_review(ctx, task_id: str, pr_url: str):
    result = await review_pipeline.execute(pr_url)
    return {"task_id": task_id, "findings": result}

class WorkerSettings:
    functions = [run_agent_review]
    redis_settings = RedisSettings()
    max_jobs = 10
    job_timeout = 3600
    max_tries = 3
    retry_delay = 30
```

| 特性 | 支持情况 |
|------|---------|
| 可靠性 | Redis 持久化 |
| 重试机制 | 内置指数退避 |
| 并发控制 | 内置 max_jobs |
| 扩展性 | 水平扩展 worker |

### 模式 4: Durable Execution（Inngest 风格）

```python
async def durable_review(ctx, task_id: str, pr_url: str):
    diff = await ctx.step("fetch_diff", lambda: fetch_pr_diff(pr_url))
    reviews = await ctx.step("multi_review", lambda: parallel_review(diff))
    consensus = await ctx.step("consensus", lambda: compute_consensus(reviews))
    await ctx.step("publish", lambda: publish_to_github(pr_url, consensus))
    return consensus
```

每步自动持久化，失败后从断点恢复。

### 模式 5: 分布式任务队列（Hatchet）

Hatchet 对比 FastAPI BackgroundTasks:

| 特性 | FastAPI BG | Hatchet |
|------|-----------|---------|
| 可观测性 | 无 | 完整 dashboard |
| 可靠性 | 任务可能丢失 | 保证执行 |
| 重试 | 手动实现 | 内置策略 |
| 并发控制 | 无 | 可配置限制 |
| 扩展 | 绑定 web 服务器 | 独立 worker |

---

## 三、hermes_free 推荐方案

### 分层执行策略

```python
class TaskExecutor:
    async def execute(self, task: Task) -> str:
        if task.estimated_duration < 30:
            return await self._run_inline(task)
        elif task.estimated_duration < 3600:
            job = await self.arq_pool.enqueue_job("run_agent_task", task.id)
            return job.job_id
        else:
            job = await self.arq_pool.enqueue_job("run_durable_task", task.id)
            return job.job_id
```

### 并发控制

```python
class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 10, max_per_provider: int = 5):
        self._global_sem = asyncio.Semaphore(max_concurrent)
        self._provider_sems = {
            provider: asyncio.Semaphore(max_per_provider)
            for provider in ["openai", "anthropic", "ollama"]
        }
```

### SSE 实时任务状态

```python
@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str):
    async def event_generator():
        async for event in event_store.subscribe(task_id):
            yield {"event": event.type, "data": json.dumps(event.data)}
    return EventSourceResponse(event_generator())
```

---

## 四、参考资源

- Async Python for AI Agent Engineering
- FastAPI Background Tasks vs ARQ + Redis
- From FastAPI Background Tasks to Hatchet
- The LLM as a Microservice: Architecting for the High-Latency Era
