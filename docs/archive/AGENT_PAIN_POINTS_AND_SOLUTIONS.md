# Agent Architecture Pain Points & Solutions

> hermes_free 项目当前架构痛点分析与解决方案
> 生成日期: 2026-04-30

---

## 一、当前架构概览

hermes_free 采用 Python FastAPI + Vue 3 技术栈，已有：
- 6个 YAML 定义的 Agent (Dispatcher, Developer, Reviewer, Tester, Researcher, DevOps)
- 基于 OpenAI Agents SDK 的 agent_manager + orchestrator
- SSE 实时推送、WebSocket 终端
- asyncio.create_task 驱动的异步模式
- SQLite 持久化（成本、审查、trace、聊天）

---

## 二、核心痛点清单

### 痛点 1: 单体 Agent 认知瓶颈

**现象**: 单个 Agent 工具超过 10-15 个时性能急剧下降（Anthropic 研究证实）。当前 6 个 Agent 共享同一个 orchestrator，工具描述累积在 context window 中。

**根因**: 没有 Subagent 拆分机制，每个 Agent 需要理解所有工具。

**解决方案**:
- 实现 Subagent 架构：每个 Agent 只持有自己需要的工具子集
- 工具按需注入：运行时根据任务动态加载工具描述
- 参考: Claude Code 的 skills/MCP 按需加载模式

### 痛点 2: 长时间任务阻塞

**现象**: Agent 运行可能持续数分钟到数小时（代码审查、多模型共识），当前 asyncio.create_task 无持久化，进程重启任务丢失。

**根因**: 缺乏可靠的任务队列和持久化机制。

**解决方案**:
- 轻量级: ARQ + Redis（asyncio-native，比 Celery 更轻）
- 中量级: Inngest 风格的 durable execution（step-level 重试和可观测性）
- 重量级: Hatchet（自带 dashboard、重试策略、并发控制）
- 参考: FastAPI BackgroundTasks 仅适合 fire-and-forget，不适合长时间任务

### 痛点 3: 缺乏事件溯源

**现象**: Agent 状态存储在内存中（orchestrator 的字典），无法审计决策链路，无法回放失败场景。

**根因**: CRUD 式状态管理，覆盖写入而非追加事件。

**解决方案**:
- 实现 Event Sourcing: 每个状态变更作为不可变事件追加到 event log
- 配合 CQRS: 写模型（event store）与读模型（projection）分离
- ESAA 模式: Agent 不直接写状态，而是发射意图和建议的 diff，由确定性编排器验证并应用
- 参考: arxiv ESAA 论文 (2602.23193)

### 痛点 4: Agent 间上下文传递低效

**现象**: Agent handoff 时传递原始对话历史，token 浪费严重。CrewAI 基准测试显示 18% 的 token 开销来自上下文传递。

**根因**: 缺乏结构化的 handoff 协议。

**解决方案**:
- 结构化 handoff 包: goal statement + completed steps + relevant findings + open questions + constraints + recommended next step
- Subagent delegation: 每个 subagent 有独立 context window，只返回 1000-2000 token 的摘要
- 参考: Claude Code 的 Fork/Teammate/Worktree 三种 subagent 执行模型

### 痛点 5: 缺乏 Warm Pool 机制

**现象**: 每次 Agent 启动都需要重新初始化（加载配置、建立连接、验证权限），冷启动延迟明显。

**根因**: 没有预热和连接池复用机制。

**解决方案**:
- LLM API 连接池: httpx.AsyncClient 复用，预建连接
- Agent 实例池: 维护预初始化的 Agent 实例，按需分配
- Provider 连接预热: 启动时预建到各 provider 的连接
- 模型权重预加载: 对本地模型（Ollama）实现 WarmServe 风格的预热
- 参考: AWS SageMaker Warm Pools, WarmServe (arxiv 2512.09472)

### 痛点 6: 缺乏任务依赖图和 DAG 编排

**现象**: 当前 Agent 任务是线性执行或简单的 asyncio.gather 并行，无法表达复杂的依赖关系。

**根因**: 缺乏 DAG（有向无环图）任务编排引擎。

**解决方案**:
- 任务依赖图: 每个任务声明前置依赖，依赖满足后自动调度
- 三阶段流水线: Task Decomposition -> Worker Loop (并发) -> Review & Fix
- 参考: LangGraph 的状态图、Atomic 的 graph executor

### 痛点 7: 可观测性不足

**现象**: tracing_store 只记录 run/span，缺乏端到端的 distributed tracing、成本归因、性能分析。

**根因**: 缺乏统一的事件驱动可观测性层。

**解决方案**:
- 统一事件总线: 所有 Agent 操作通过事件总线广播
- 结构化 trace: 每个 span 包含 input_tokens, output_tokens, latency, cost, model
- 成本归因: 按 task/session/agent 三级归因
- 参考: LangSmith, Arize Phoenix

### 痛点 8: Guardrails 与 Agent 行为不一致

**现象**: guardrails.py 和 structured_guardrails.py 逻辑分散，审批流不完整。

**根因**: 缺乏分层约束模型。

**解决方案**:
- 分层约束: P0 (硬阻断) > P1 (需确认) > P2 (警告) > P3 (日志)
- 确定性守卫 + LLM 守卫分离: 语法检查用确定性规则，语义检查用 LLM
- 参考: Anthropic 的 tiered constraint model

---

## 三、优先级排序

| 优先级 | 痛点 | 影响范围 | 实现难度 |
|--------|------|----------|----------|
| P0 | 长时间任务阻塞 | 全局 | 中 |
| P0 | 缺乏事件溯源 | 全局 | 高 |
| P1 | Subagent 拆分 | Agent 系统 | 中 |
| P1 | 上下文传递低效 | Agent 间通信 | 低 |
| P1 | 任务 DAG 编排 | 任务系统 | 中 |
| P2 | Warm Pool | 性能优化 | 中 |
| P2 | 可观测性 | 运维 | 中 |
| P3 | Guardrails 一致性 | 安全 | 低 |

---

## 四、参考资源

| 来源 | 重点 |
|------|------|
| Anthropic Harness Design | 长时间运行 harness 设计 |
| LangChain Anatomy of Harness | Agent = Model + Harness |
| ESAA Event Sourcing (arxiv 2602.23193) | Agent 事件溯源 |
| Inngest Durable Execution | 持久化执行 |
| Azure Agent Patterns | 编排模式 |
| Addy Osmani Harness Engineering | 四大支柱 |
