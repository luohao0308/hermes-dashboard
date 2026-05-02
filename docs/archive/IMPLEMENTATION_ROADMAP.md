# Implementation Roadmap

> hermes_free Agent 架构升级实施路线图
> 生成日期: 2026-04-30

---

## 文档索引

| 文档 | 主题 | 核心内容 |
|------|------|----------|
| AGENT_PAIN_POINTS_AND_SOLUTIONS.md | 痛点分析 | 8 大痛点 + 优先级排序 |
| MULTI_AGENT_ORCHESTRATION.md | 多Agent编排 | 6 种编排模式 + 框架对比 + 推荐方案 |
| AGENT_HARNESS_DESIGN.md | Harness 设计 | 四大支柱 + Hooks + 长时间运行 |
| EVENT_SOURCING_FOR_AGENTS.md | 事件溯源 | ESAA + CQRS + Event Store 实现 |
| ASYNC_EXECUTION_PATTERNS.md | 异步执行 | 5 种模式对比 + 分层策略 |
| TASK_DECOMPOSITION_AND_WARM_POOL.md | 任务拆解+预热 | DAG 引擎 + 连接池 + Agent 池 |

---

## 实施阶段

### Phase 1: 基础设施（1-2 周）

目标: 解决 P0 痛点 - 长时间任务阻塞

1. **引入 ARQ + Redis 任务队列**
   - 安装: pip install arq
   - 创建 backend/tasks/worker.py
   - 配置 WorkerSettings（max_jobs, timeout, retries）
   - FastAPI 路由改为 enqueue_job

2. **实现连接池**
   - 创建 backend/pool/connection_pool.py
   - LLMConnectionPool: httpx.AsyncClient 复用
   - ProviderWarmPool: 启动时预热

3. **任务状态 SSE 端点**
   - /api/tasks/{task_id}/events SSE 流
   - 前端 TaskPanel 组件订阅

交付物:
- backend/tasks/worker.py
- backend/tasks/arq_worker.py
- backend/pool/connection_pool.py
- backend/pool/warm_pool.py
- 更新 backend/main.py 路由

---

### Phase 2: 事件溯源（2-4 周）

目标: 解决 P0 痛点 - 缺乏审计和回放

1. **Event Store**
   - 创建 backend/events/event_store.py
   - SQLite-backed append-only event log
   - Event dataclass + EventType enum

2. **Event Emitter**
   - 创建 backend/events/emitter.py
   - 在 orchestrator 中植入事件发射
   - 所有 Agent 操作产生事件

3. **Projections（读模型）**
   - 创建 backend/events/projections.py
   - TaskProjection: 从事件重建状态
   - CostProjection: 从事件计算成本

4. **前端 Event Timeline**
   - 更新 TraceTimeline 组件
   - 展示完整事件链

交付物:
- backend/events/event_store.py
- backend/events/emitter.py
- backend/events/projections.py
- 更新 backend/agent/orchestrator.py

---

### Phase 3: Subagent 架构（4-6 周）

目标: 解决 P1 痛点 - Agent 认知瓶颈

1. **工具按需分配**
   - 定义 AGENT_TOOLS 映射
   - 每个 Agent 只持有自己的工具子集

2. **Subagent Spawner**
   - 创建 backend/agent/subagent.py
   - Fork / Isolated 两种模式
   - 结果压缩器

3. **Agent 实例池**
   - 创建 backend/pool/agent_pool.py
   - 预初始化 Agent 实例
   - 按需分配和归还

4. **Handoff 协议**
   - HandoffPackage dataclass
   - 结构化上下文传递

交付物:
- backend/agent/subagent.py
- backend/agent/handoff.py
- backend/pool/agent_pool.py
- 更新 backend/agent/agent_manager.py

---

### Phase 4: DAG 编排（6-10 周）

目标: 解决 P1 痛点 - 任务依赖和并行

1. **TaskDAG 引擎**
   - 创建 backend/orchestrator/dag_engine.py
   - 依赖分析 + 拓扑排序
   - 并发执行同层任务

2. **Planner Agent**
   - 创建 backend/agent/planner.py
   - 需求 -> 任务 DAG
   - 只读，不执行

3. **Worker Loop**
   - 创建 backend/orchestrator/worker_loop.py
   - 按 DAG 调度
   - 重试 + 超时 + 并发限制

4. **Reviewer Agent**
   - 创建 backend/agent/reviewer.py
   - 审计 Worker 输出
   - 条件路由: 通过/修复

交付物:
- backend/orchestrator/dag_engine.py
- backend/orchestrator/worker_loop.py
- backend/agent/planner.py
- backend/agent/reviewer.py

---

### Phase 5: 可观测性 + 优化（10-14 周）

1. **统一事件总线** - 进程内 pub/sub
2. **成本归因** - 按 task/session/agent/model 四级
3. **Context Manager** - Compaction + JIT retrieval + Token 预算
4. **Guardrails 分层** - P0-P3 约束层级

---

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 任务队列 | ARQ + Redis | asyncio-native，比 Celery 轻 |
| HTTP 客户端 | httpx | async + HTTP/2 + 连接池 |
| 事件存储 | SQLite | 与现有 cost_tracker 一致 |
| 前端实时 | SSE | 已有 sse_manager |
| Agent 框架 | 保持 OpenAI SDK | 渐进式改造 |

---

## 依赖关系

```
Phase 1 (ARQ + 连接池)  --------+
                                 |
Phase 2 (事件溯源)  -------------+
                                 |
Phase 3 (Subagent) <- Phase 1 --+
                                 |
Phase 4 (DAG 编排) <- Phase 3 --+
                                 |
Phase 5 (可观测性) <- Phase 2 --+
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ARQ + Redis 增加运维复杂度 | 中 | Docker Compose 一键部署 |
| 事件溯源改造量大 | 高 | 渐进式：先 Agent 操作，再扩展 |
| Subagent 拆分后调试困难 | 中 | 统一 trace_id 贯穿 |
| DAG 引擎死锁 | 高 | 拓扑排序检测环 + 超时保护 |
