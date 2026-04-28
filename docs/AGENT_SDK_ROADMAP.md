# OpenAI Agents SDK 能力延伸路线图

## 背景

Hermès Dashboard 现在已经具备 AgentOps 概览、Session 复盘、Chat 持久化、告警建议、终端安全和系统配置中心。下一阶段的核心问题不是“再加页面”，而是让系统从观察面板升级成可解释、可编排、可验证的 Agent 工作流平台。

OpenAI Agents SDK 的关键能力包括：

- Agent：用 instructions、tools、handoffs、guardrails、structured outputs 组合运行时行为
- Function tools：把 Python 函数变成带 schema 校验的工具
- Handoffs：让调度 Agent 把任务交给专业 Agent，并可携带结构化上下文
- Guardrails：对输入、输出和工具调用做验证与拦截
- Tracing：记录 LLM 调用、工具调用、handoff、guardrail 等运行轨迹
- Sessions：为多轮 Agent 运行保留上下文历史

参考：

- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/agents/
- https://openai.github.io/openai-agents-python/tools/
- https://openai.github.io/openai-agents-python/handoffs/
- https://openai.github.io/openai-agents-python/guardrails/
- https://openai.github.io/openai-agents-python/tracing/
- https://openai.github.io/openai-agents-python/sessions/

## 现有痛点

1. 用户能看到失败，但仍要人工判断失败发生在模型、工具、网络、终端还是配置层。
2. 多 Agent handoff 只以文本事件展示，缺少结构化原因、输入摘要、责任边界和结果评价。
3. 工具调用缺少权限分级，危险操作只能靠终端命令拦截，Agent 工具层还没有统一 guardrail。
4. Chat、Session 复盘、日志、终端虽然已经连起来一部分，但还没有形成“工作流事件图”。
5. 告警现在是规则型，不能自动归因、聚合相似问题，也不能生成 runbook。
6. 缺少评估体系：不知道哪个 Agent 配置更好，哪个 handoff 更稳定，哪个工具最容易失败。

## 产品方向

把 Hermès Dashboard 升级为 Agent Workflow Control Plane：

- 观察：知道 Agent 当前在做什么
- 复盘：知道任务为什么失败
- 编排：知道应该交给哪个 Agent
- 校验：知道输出和工具调用是否安全可信
- 追踪：知道每一步的成本、耗时、输入、输出和责任 Agent
- 改进：能基于历史运行自动提出配置和 prompt 优化建议

## Roadmap

### Phase A: Trace-first 工作流追踪

目标：把一次 Agent run 的模型输出、工具调用、handoff、guardrail 统一展示成 trace timeline。

任务清单：

- [x] 后端新增 `agent_run_id`，把 chat message、handoff、tool event 统一挂到同一运行 ID
- [x] 本地保存 trace span 摘要
- [x] 新增 `GET /api/agent/runs/{run_id}/trace`
- [x] 前端 SessionDetail 增加 Trace timeline：tool、handoff、input、output、error 分段展示
- [ ] Trace 节点显示耗时、token、Agent 名、工具名、输入摘要和输出摘要
- [ ] 测试：模拟 handoff/tool event 后，trace API 返回稳定 schema

验收标准：

- 用户能从一次失败任务看到最后一个失败 span
- 每个 handoff 都能看到 from/to/reason
- 每个 tool call 都有状态、耗时和输出摘要

### Phase B: Guardrails-first 安全与质量门禁

目标：把危险动作和低质量输出拦在 Agent 工作流内部，而不只是终端层。

任务清单：

- [x] 定义工具风险等级：read、write、execute、network、destructive
- [x] 为工具调用新增 allow/deny/confirm 策略
- [ ] 接入 Agents SDK guardrails，对输入和输出做 Pydantic 校验
- [ ] 新增 tool guardrail：危险 shell/git/file 操作要求人工确认
- [x] 前端新增 Guardrail 事件视图：拦截原因、建议动作、确认按钮
- [x] 后端新增 `POST /api/agent/guardrails/{event_id}/approve`
- [x] 测试：confirm 工具调用审批后才继续

验收标准：

- Agent 无法静默执行 destructive 工具调用
- 输出结构不合格时能自动标记并要求修复或降级
- 所有 guardrail 事件进入 trace 和告警面板

### Phase C: Function Tools 能力库

目标：把 Hermès Dashboard 已有 API 变成 Agent 可调用的安全工具。

任务清单：

- [x] 封装 `get_status_tool`
- [x] 封装 `search_sessions_tool`
- [x] 封装 `get_session_messages_tool`
- [x] 封装 `get_logs_tool`
- [ ] 封装 `create_alert_summary_tool`
- [ ] 封装 `terminal_session_list_tool`
- [x] 为第一批工具定义输入 schema、风险等级和错误处理
- [x] 前端 System 页面显示工具清单和风险等级

验收标准：

- Analyst Agent 可以基于工具自动生成失败复盘
- Monitor Agent 可以用工具聚合告警
- 工具失败不会导致整个 Agent run 崩溃

### Phase D: 结构化 Handoff 编排

目标：让多 Agent 协作从“模型自由交接”变成可审计的工作流。

任务清单：

- [ ] 为 handoff 定义 `reason`、`priority`、`expected_output`、`context_refs`
- [ ] 调度 Agent handoff 前必须输出结构化 handoff payload
- [ ] 后端保存 handoff payload 到 trace
- [x] 前端 Agent 配置页增加 handoff 拓扑图
- [ ] SessionDetail 显示每次 handoff 的原因和结果
- [ ] 添加 handoff 失败回退策略：回到 Dispatcher 或转 Reviewer

验收标准：

- 用户能理解为什么从 Developer 转到 Reviewer
- 每次 handoff 都有输入摘要和期望产物
- handoff 失败不会丢失上下文

### Phase D0: Chat 与 Session 双向绑定

目标：让用户从失败复盘无缝进入 Agent Chat，并让 Agent 自动携带 Hermès session 证据上下文。

任务清单：

- [x] SessionDetail 增加“继续对话”入口
- [x] Agent Chat 支持通过 `#/chat?linked_session_id=...` 打开或复用关联对话
- [x] Chat header 显示关联 Hermès session 并可返回复盘页
- [x] 后端 Agent 运行时注入 linked session 摘要和最新 RCA
- [x] trace 记录 linked session context span
- [x] Chat 消息区展示关联 session 的 RCA/trace 快捷卡片

验收标准：

- 用户能从 session 复盘一键进入带上下文的 Chat
- Agent 回答时知道关联 session 的状态、消息摘要和 RCA
- 用户能从 Chat 返回对应 session 复盘页

### Phase E: AI Root Cause Analyst

目标：把 Phase 2 的规则型失败初判升级成 Agent 辅助 RCA。

任务清单：

- [x] 新增 RCA Analyst 分析器（先以确定性规则产出，后续可替换为 Agents SDK Agent）
- [x] RCA 分析使用 session、logs、trace 证据
- [x] 输出结构化 RCA：root_cause、evidence、confidence、next_actions
- [x] 前端 SessionDetail 增加“一键分析失败原因”
- [x] RCA 结果可保存到 session trace 数据库
- [x] RCA 低置信度时提示人工查看原始 trace
- [ ] RCA Agent 接入 config 工具和真实 Agents SDK structured output

验收标准：

- 对失败 session 能生成证据链而不是泛泛建议
- RCA 输出必须引用日志或 trace 节点
- 用户能把 RCA 结果复制到 issue/PR/Notion

### Phase F: Runbook 自动化

目标：把常见问题沉淀成可复用的处理流程。

任务清单：

- [x] 定义首版 runbook schema：severity、summary、evidence、checklist、markdown
- [ ] 从告警面板触发 runbook
- [x] 支持只读 runbook：收集 session、RCA、trace
- [ ] 支持半自动 runbook：需要用户确认后执行修复动作
- [x] 前端 SessionDetail 显示并复制 Runbook 产物
- [x] 失败 runbook 自动生成复盘记录
- [x] 支持 RCA/Runbook Markdown 本地导出，为 Obsidian/Notion 同步打底
- [ ] 前端新增 Runbook 执行时间线

验收标准：

- Gateway 不可达、日志爆错、session 卡住都有对应 runbook
- destructive 步骤必须人工确认
- runbook 产物进入 SessionDetail 和 Chat 上下文

### Phase G: Eval 与配置优化

目标：让 Agent 配置调整有数据依据。

任务清单：

- [ ] 定义评估样例集：debug、review、research、deploy、monitor
- [x] 记录每个 run 的成功率、耗时、handoff 次数、tool 次数、guardrail 次数
- [x] 新增 Agent 配置静态评分：主 Agent、handoff 可达性、孤立节点
- [ ] 新增 Agent 配置 A/B 对比
- [ ] Reviewer Agent 自动给 prompt/config 改进建议
- [ ] System 页面展示 Agent 性能趋势
- [ ] CI 增加轻量离线 schema/eval 测试

验收标准：

- 能看出哪个 Agent 配置导致更多失败
- prompt 改动前后有可比较指标
- 高风险配置不会直接进入默认 main_agent

## 优先级建议

1. Phase A Trace-first 工作流追踪
2. Phase B Guardrails-first 安全与质量门禁
3. Phase C Function Tools 能力库
4. Phase E AI Root Cause Analyst
5. Phase D 结构化 Handoff 编排
6. Phase F Runbook 自动化
7. Phase G Eval 与配置优化

推荐先做 A+B+C。原因是 trace、guardrails 和 tools 是 Agent 平台能力地基；没有这三件事，RCA、runbook 和 eval 都会缺少可信数据。

## 下一批实施任务

- [x] 创建 `backend/agent/tools/`，实现 Hermès API 工具封装
- [x] 创建 `backend/agent/tracing_store.py`，保存本地 trace span
- [x] 扩展 `_classify_chat_event`，识别 tool、handoff 并写入 trace
- [x] 新增 `GET /api/agent/runs/{run_id}/trace`
- [x] 新增 `frontend/src/components/TraceTimeline.vue`
- [x] 在 SessionDetail 接入 Trace timeline
- [x] 新增 guardrail 策略配置文件 `backend/agent/guardrails.yaml`
- [ ] 为危险工具调用增加 confirm/approve API
- [x] 增加单元测试：trace store、tool schema、guardrail deny、RCA analyzer
- [ ] 增加 E2E：打开失败 session，查看 trace，触发 RCA
