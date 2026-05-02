# Agent Harness Design Principles

> Agent Harness 工程设计原则与 hermes_free 落地方案
> 生成日期: 2026-04-30

---

## 一、核心公式

> Agent = Model + Harness. If you're not the model, you're the harness.
> -- LangChain, 2026

Harness 是模型之外的一切：代码、配置、执行逻辑。

```
┌─────────────────────────────────────────┐
│              Agent Harness              │
├─────────────┬───────────┬───────────────┤
│ System      │ Tools &   │ Orchestration │
│ Prompts     │ Skills    │ Logic         │
├─────────────┼───────────┼───────────────┤
│ Hooks &     │ Context   │ Observability │
│ Middleware  │ Mgmt      │ & Tracing     │
├─────────────┼───────────┼───────────────┤
│ Sandboxing  │ Subagent  │ Memory &      │
│ & Safety    │ Spawning  │ Persistence   │
└─────────────┴───────────┴───────────────┘
```

---

## 二、四大支柱（Addy Osmani）

### 支柱 1: System Prompt（系统提示）

**原则**: 编写系统提示更接近写软件规格说明，而不是写聊天机器人人设。

**层级约束模型** (Anthropic 2026):
```
P0: 绝对不可违反（安全、合规）
P1: 强烈建议遵守（最佳实践）
P2: 一般建议（风格偏好）
P3: 可选（锦上添花）
```

**hermes_free 落地**:
- 当前 agents.yaml 中的 prompt 是扁平的文本
- 改进: 引入分层 prompt 结构，每个 Agent 的 system prompt 包含身份、工具目录、推理协议、硬约束、输出格式、升级条件

### 支柱 2: Tools & Skills（工具与技能）

**原则**: 单个 Agent 工具不超过 10-15 个。超过则拆分为 subagent。

**hermes_free 现状**:
- hermes_tools.py 定义了所有工具
- 所有 Agent 共享同一套工具集

**改进方案**:
```python
# 按角色分配工具子集
AGENT_TOOLS = {
    "dispatcher": ["route_task", "get_status"],
    "developer": ["read_file", "write_file", "run_tests", "search_code"],
    "reviewer": ["read_file", "analyze_code", "post_comment"],
    "tester": ["run_tests", "generate_test", "check_coverage"],
    "researcher": ["web_search", "read_docs", "summarize"],
    "devops": ["deploy", "check_logs", "rollback"],
}
```

### 支柱 3: Context Management（上下文管理）

**问题**: Context window 越大，指令遵循能力越差。即使百万 token 窗口也会退化。

**5 种生产级策略**:

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| Compaction | 压缩对话历史为摘要 | 对话长度超限 |
| Observation Masking | 隐藏旧的工具输出，保留调用记录 | 工具输出冗长 |
| Just-in-time Retrieval | 只存轻量标识符，按需加载 | 文件操作 |
| Sub-agent Delegation | 子 Agent 独立探索，只返回摘要 | 探索性任务 |
| Full Context Reset | 销毁会话，从 handoff 文件重建 | 超长时间任务 |

**hermes_free 落地**:
```python
class ContextManager:
    """上下文管理器 - 实现 compaction 和 JIT retrieval"""

    async def compact_if_needed(self, messages: list, threshold: float = 0.8):
        """当 token 使用超过阈值时压缩"""
        token_count = self.count_tokens(messages)
        if token_count > self.max_tokens * threshold:
            summary = await self.summarize(messages[:len(messages)//2])
            return [summary] + messages[len(messages)//2:]
        return messages

    async def jit_load(self, file_ref: str) -> str:
        """按需加载文件内容，而非预加载"""
        return await self.read_head(file_ref, lines=50)
```

### 支柱 4: Subagent Orchestration（子 Agent 编排）

**3 种执行模型** (Claude Code):

| 模型 | 隔离级别 | 通信方式 | 适用场景 |
|------|----------|----------|----------|
| Fork | 父 context 的字节级副本 | 共享 context | 快速子任务 |
| Teammate | 独立终端面板 | 文件邮箱 | 并行协作 |
| Worktree | 独立 git worktree | Git 互操作 | 独立开发 |

**hermes_free 落地**:
```python
class SubagentSpawner:
    """子 Agent 生成器"""

    async def spawn_fork(self, parent_context: Context, task: str) -> Result:
        """Fork 模式: 共享父 context"""
        child = Agent(context=parent_context, tools=self.get_tools(task))
        return await child.run(task)

    async def spawn_isolated(self, task: str, tools: list[str]) -> Result:
        """Isolated 模式: 独立 context window"""
        child = Agent(tools=tools, max_tokens=4096)
        result = await child.run(task)
        return self.condense(result, max_tokens=2000)  # 只返回摘要
```

---

## 三、Hooks 系统设计

**Hook 类型**:
- **PreToolUse**: 工具执行前（参数验证、权限检查）
- **PostToolUse**: 工具执行后（格式化、检查）
- **PreAgentRun**: Agent 启动前（上下文注入）
- **PostAgentRun**: Agent 结束后（结果验证、清理）
- **OnHandoff**: Agent 间交接时（上下文压缩、格式转换）

**hermes_free 落地**:
```python
class HookRegistry:
    """Hook 注册中心"""

    def __init__(self):
        self._hooks: dict[str, list[Callable]] = defaultdict(list)

    def register(self, event: str, handler: Callable, priority: int = 0):
        self._hooks[event].append(HookEntry(handler, priority))
        self._hooks[event].sort(key=lambda h: h.priority)

    async def trigger(self, event: str, context: dict) -> dict:
        for hook in self._hooks[event]:
            context = await hook.handler(context)
        return context
```

---

## 四、长时间运行 Harness（Anthropic 模式）

Anthropic 2026 提出的三 Agent Harness 架构：

```
Planner Agent          Generator Agent        Evaluator Agent
(分解任务)      --->   (生成代码)       --->  (评估质量)
    ^                                              |
    |______________________________________________|
                    (迭代改进)
```

**关键设计原则**:

1. **分离关注点**: 规划、生成、评估由不同 Agent 负责
2. **迭代改进**: 评估不通过时回退到 Generator
3. **上下文重置**: 长时间运行时定期重置 context，从 handoff 文件恢复
4. **Harness 简化**: "找到最简单的可行方案，只在需要时增加复杂度"
5. **模型演进**: 新模型发布时重新审视 harness，移除不再需要的组件

**hermes_free 落地**:
```python
class LongRunningHarness:
    """长时间运行的 Harness"""

    async def run(self, spec: str):
        # Phase 1: 规划
        task_list = await self.planner.decompose(spec)

        for task in task_list:
            # Phase 2: 生成（带上下文重置）
            if self.context_too_large():
                handoff = await self.create_handoff_file()
                await self.reset_context(handoff)

            code = await self.generator.implement(task)

            # Phase 3: 评估
            evaluation = await self.evaluator.assess(code, task)
            if not evaluation.passed:
                code = await self.generator.fix(code, evaluation.feedback)

            await self.commit(code)
```

---

## 五、观测性设计

**三层观测**:

```
Layer 1: Structured Logging (结构化日志)
  - 每个 Agent 操作记录: timestamp, agent_id, action, input_tokens, output_tokens, latency_ms

Layer 2: Distributed Tracing (分布式追踪)
  - trace_id 贯穿整个任务生命周期
  - span 嵌套: task -> agent -> tool_call -> llm_call

Layer 3: Cost Attribution (成本归因)
  - 按 task/session/agent/model 四级归因
  - 预算告警: 超过阈值自动降级或暂停
```

---

## 六、参考资源

- LangChain: The Anatomy of an Agent Harness
- Anthropic: Harness Design for Long-Running Apps
- Addy Osmani: Agent Harness Engineering
- Arize AI: Context Management in Agent Harnesses
- InfoQ: Anthropic Three-Agent Harness
- Inngest: Your Agent Needs a Harness, Not a Framework
