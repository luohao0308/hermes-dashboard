# AI Workflow Control Plane — 真实场景验收计划

> 用于验证平台是否真正解决 AI 工作流的可观察性、治理、复盘和运维痛点。
> 本文档面向产品负责人、工程负责人和测试人员。

## 1. 验收目标

| # | 目标 | 衡量方式 |
|---|------|----------|
| G1 | AI 工作流失败时，能否在 5 分钟内定位根因？ | 记录从告警到定位的时间 |
| G2 | RCA 报告是否引用了有效证据（trace span、日志、工具调用记录）？ | 人工评审 RCA 证据链 |
| G3 | Runbook 是否可直接执行，而非泛泛建议？ | 按 Runbook 步骤操作，记录完成率 |
| G4 | 高风险工具调用是否被 Approval 拦截？ | 模拟危险操作，验证拦截率 |
| G5 | 审计日志能否追溯到"谁、在什么时间、做了什么"？ | 随机抽查 10 条审计记录 |
| G6 | 健康面板能否帮助运维人员定位系统级问题？ | 模拟组件故障，验证发现速度 |
| G7 | 中文团队能否无门槛使用界面？ | 中文 UI 覆盖率 + 反馈表评分 |

**不验证的内容：**
- 不验证新功能开发（本轮无新功能）
- 不验证 SSO/OIDC（属于 v3.1 候选）
- 不验证性能基准测试（属于独立压测阶段）

---

## 2. 试点场景选择

选择 3 个覆盖不同业务类型的场景，确保验证覆盖面。

### 场景 A：GitHub PR / Code Review Workflow

**业务背景：** 团队使用 AI 辅助代码审查，Agent 自动分析 PR diff、生成审查意见、标记风险代码。

| 角色 | 说明 |
|------|------|
| Runtime | GitHub Review Agent（基于 Claude/GPT 的代码审查 Agent） |
| 触发方式 | PR 创建或更新时，Webhook 触发 Connector |
| 典型工具调用 | `get_pr_diff`、`analyze_code`、`post_review_comment` |
| 人工审批点 | 高风险文件变更（如 `Dockerfile`、`.env`、`deploy.yml`）需人工确认后才提交审查意见 |
| 预期产物 | 审查意见 Artifact、风险评分 EvalResult |

### 场景 B：CI/CD 或自动化任务 Workflow

**业务背景：** 团队使用 AI Agent 辅助 CI/CD 流程，如自动修复构建失败、生成 changelog、部署前检查。

| 角色 | 说明 |
|------|------|
| Runtime | CI/CD Agent（Jenkins/GitHub Actions 集成的 AI 辅助） |
| 触发方式 | CI 流水线失败时，自动创建 Run |
| 典型工具调用 | `read_build_log`、`suggest_fix`、`create_pr`、`trigger_deploy` |
| 人工审批点 | `trigger_deploy` 为高风险操作，需审批 |
| 预期产物 | 修复建议 Artifact、部署前检查报告 |

### 场景 C：Agent / LLM 工具调用 Workflow

**业务背景：** 团队运行多步 Agent 任务（如数据查询、报告生成、知识检索），涉及多个工具调用和 handoff。

| 角色 | 说明 |
|------|------|
| Runtime | 内部 Agent 平台（LangChain / 自研 Agent） |
| 触发方式 | 用户发起任务或定时调度 |
| 典型工具调用 | `query_database`、`search_knowledge`、`generate_report`、`send_notification` |
| 人工审批点 | `query_database` 如涉及生产数据，需审批；`send_notification` 如发送外部邮件，需审批 |
| 预期产物 | 报告 Artifact、执行 trace |

---

## 3. 每个场景的接入方式

### 3.1 Connector 配置

每个场景注册一个 Connector，通过事件摄入 API 上报数据。

```bash
# 创建 Connector
curl -X POST http://localhost:8000/api/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "github-review-agent",
    "connector_type": "webhook",
    "config": {
      "webhook_secret": "<hmac-secret>"
    }
  }'
```

### 3.2 事件上报流程

```
Agent 执行 → 捕获事件 → POST /api/connectors/{id}/events → 平台记录
```

事件类型映射：

| Agent 执行阶段 | 事件类型 | 平台对象 |
|---------------|----------|----------|
| 任务开始 | `run.start` | Run（status=running） |
| 用户输入 | `span.create` | TraceSpan（type=user_input） |
| 模型调用 | `span.create` | TraceSpan（type=model_call） |
| 工具调用 | `tool.call` | ToolCall + TraceSpan（type=tool_call） |
| Agent 交接 | `span.create` | TraceSpan（type=handoff） |
| 需要审批 | `approval.request` | Approval（status=pending） |
| 任务结束 | `run.complete` / `run.fail` | Run（status=completed/failed） |
| 产出物 | `artifact.create` | Artifact |

### 3.3 各场景的 Run 与 TraceSpan 结构

**场景 A — PR Review：**

```
Run: "PR #123 Code Review"
├── TraceSpan: user_input — "Review PR #123"
├── TraceSpan: model_call — Claude 分析 diff（input_tokens=2000, output_tokens=500）
├── TraceSpan: tool_call — get_pr_diff（status=completed）
├── TraceSpan: tool_call — analyze_code（status=completed）
├── TraceSpan: handoff — Developer → Reviewer（reason="需要审查高风险文件"）
├── TraceSpan: tool_call — post_review_comment（status=pending_approval）
│   └── Approval: "确认发布审查意见"（risk_level=high）
└── TraceSpan: model_call — 生成最终报告
```

**场景 B — CI/CD Fix：**

```
Run: "修复构建失败 #456"
├── TraceSpan: user_input — "构建失败，请分析"
├── TraceSpan: tool_call — read_build_log（status=completed）
├── TraceSpan: model_call — 分析错误原因
├── TraceSpan: tool_call — suggest_fix（status=completed）
├── TraceSpan: tool_call — create_pr（status=completed）
├── TraceSpan: tool_call — trigger_deploy（status=pending_approval）
│   └── Approval: "确认部署到 staging"（risk_level=critical）
└── TraceSpan: model_call — 生成部署报告
```

**场景 C — Multi-tool Agent：**

```
Run: "生成月度数据报告"
├── TraceSpan: user_input — "生成 2026 年 4 月报告"
├── TraceSpan: tool_call — query_database（status=pending_approval）
│   └── Approval: "查询生产数据库"（risk_level=high）
├── TraceSpan: tool_call — search_knowledge（status=completed）
├── TraceSpan: model_call — 分析数据趋势
├── TraceSpan: tool_call — generate_report（status=completed）
├── TraceSpan: tool_call — send_notification（status=pending_approval）
│   └── Approval: "发送报告邮件"（risk_level=medium）
└── Artifact: 月度报告 PDF
```

---

## 4. 人为制造失败案例

每个场景至少执行以下 5 类失败，验证 RCA、Runbook 和审计能力。

### 4.1 工具失败

**操作：** 在 Agent 中模拟工具返回错误（如 API 500、超时、参数校验失败）。

**预期平台行为：**
- TraceSpan status = `failed`，包含错误摘要
- Run status = `failed`
- RCA 识别为"工具失败"类别，引用具体 span 和错误信息
- Runbook 建议"重放工具调用"或"检查外部服务状态"

**场景 A 示例：** `get_pr_diff` 返回 GitHub API 403（rate limit）
**场景 B 示例：** `read_build_log` 返回 Jenkins 500
**场景 C 示例：** `query_database` 返回连接超时

### 4.2 超时

**操作：** 设置较短的 task timeout_seconds，让某个工具调用或模型调用超过时限。

**预期平台行为：**
- TraceSpan status = `timeout`
- Run status = `failed`（timeout）
- RCA 识别为"超时"类别，引用具体 span 的耗时
- Runbook 建议"增加超时时间"或"检查下游服务延迟"

**场景 A 示例：** 模型调用 Claude 超过 30s 未返回
**场景 B 示例：** `trigger_deploy` 超过 60s 未完成
**场景 C 示例：** `query_database` 查询复杂数据超过 45s

### 4.3 高风险工具调用

**操作：** 执行标记为 `risk_level: high` 或 `risk_level: critical` 的工具调用。

**预期平台行为：**
- ToolCall decision = `pending`，等待 Approval
- Approval 出现在审批收件箱
- 如未审批，工具调用不执行
- Audit 记录工具调用请求和审批决策

**场景 A 示例：** 修改 `Dockerfile` 的 PR 审查意见
**场景 B 示例：** `trigger_deploy` 到生产环境
**场景 C 示例：** `query_database` 查询含用户 PII 的表

### 4.4 Approval 超时或拒绝

**操作：** 创建 Approval 后不操作（模拟超时），或主动拒绝。

**预期平台行为：**
- **超时：** Approval 状态变为 `timeout`，Run 相应 task 标记为 `blocked`
- **拒绝：** Approval status = `rejected`，Run 跳过该 task 或标记为 `failed`
- Audit 记录拒绝操作和操作者
- RCA 识别为"审批被拒"类别

**场景 A 示例：** 审查意见发布审批被 reviewer 拒绝
**场景 B 示例：** 部署审批超时未响应
**场景 C 示例：** 数据库查询审批被安全团队拒绝

### 4.5 Connector 签名错误

**操作：** 使用错误的 webhook_secret 发送事件。

**预期平台行为：**
- 事件被拒绝，返回 401/403
- Audit 记录一次签名验证失败
- Health 面板 Connector Ingestion 状态异常
- 不创建任何 Run 或 TraceSpan

**验证命令：**

```bash
# 使用错误的 secret 发送事件
curl -X POST http://localhost:8000/api/connectors/{id}/events \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=wrong_signature" \
  -d '{"event_type": "run.start", "payload": {...}}'
```

---

## 5. 验收指标

### 5.1 定量指标

| # | 指标 | 目标值 | 测量方式 |
|---|------|--------|----------|
| M1 | 失败定位时间 | ≤ 5 分钟 | 从 Run status=failed 到 RCA 生成的时间 |
| M2 | RCA 证据引用率 | ≥ 80% | RCA evidence 中引用了真实 span/log 的比例 |
| M3 | Runbook 步骤可执行率 | ≥ 70% | Runbook checklist 中可直接执行的步骤占比 |
| M4 | 高风险工具拦截率 | 100% | 所有 risk_level=high/critical 的工具调用均被拦截 |
| M5 | 审计追溯完整率 | 100% | 任意操作可追溯到操作者、时间、资源 |
| M6 | 中文 UI 覆盖率 | ≥ 95% | 用户可见文案中已国际化的比例 |

### 5.2 定性指标

| # | 指标 | 通过标准 |
|---|------|----------|
| Q1 | 告警可理解性 | 测试人员无需查阅文档即可理解告警含义 |
| Q2 | RCA 可操作性 | RCA 的 next_actions 可直接指导修复 |
| Q3 | 界面一致性 | 无中英文混杂，无文案截断，无布局错乱 |
| Q4 | 信息密度 | 关键信息（状态、耗时、token）一屏可见，无需多次跳转 |

---

## 6. 验收步骤

### Step 1：Staging 部署（Day 1）

```bash
# 1. 部署后端
cd backend
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000

# 2. 部署前端
cd frontend
npm run build
# 部署到 nginx 或直接 npm run preview

# 3. 验证健康
curl http://localhost:8000/health
# 预期：database=healthy, scheduler=running

# 4. 创建测试用户
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "validator", "role": "operator"}'
```

**检查清单：**
- [ ] `/health` 返回 healthy
- [ ] 前端可访问，默认中文
- [ ] 语言切换正常（zh-CN ↔ en-US）
- [ ] SSE 实时连接正常

### Step 2：接入 Connector（Day 1-2）

为 3 个场景分别创建 Connector：

```bash
# 场景 A
curl -X POST http://localhost:8000/api/connectors \
  -d '{"name": "github-review", "connector_type": "webhook", "config": {"webhook_secret": "secret-a"}}'

# 场景 B
curl -X POST http://localhost:8000/api/connectors \
  -d '{"name": "cicd-agent", "connector_type": "webhook", "config": {"webhook_secret": "secret-b"}}'

# 场景 C
curl -X POST http://localhost:8000/api/connectors \
  -d '{"name": "llm-agent", "connector_type": "webhook", "config": {"webhook_secret": "secret-c"}}'
```

**检查清单：**
- [ ] 3 个 Connector 创建成功
- [ ] 连接器页面显示 3 个 Connector
- [ ] secret 在 API 响应中被 mask

### Step 3：创建 Workflow（Day 2）

为场景 B 和 C 创建 Workflow Definition（场景 A 为事件驱动，无需预定义 workflow）。

```bash
# 场景 B — CI/CD 修复
curl -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD 修复流程",
    "nodes": [
      {"node_id": "read_log", "type": "tool", "tool_name": "read_build_log", "timeout_seconds": 30},
      {"node_id": "analyze", "type": "llm", "timeout_seconds": 60},
      {"node_id": "suggest", "type": "tool", "tool_name": "suggest_fix"},
      {"node_id": "deploy", "type": "tool", "tool_name": "trigger_deploy", "requires_approval": true, "timeout_seconds": 120}
    ],
    "edges": [
      {"from": "read_log", "to": "analyze"},
      {"from": "analyze", "to": "suggest"},
      {"from": "suggest", "to": "deploy"}
    ]
  }'
```

**检查清单：**
- [ ] Workflow 创建成功，DAG 验证通过
- [ ] 工作流详情页显示 DAG 图
- [ ] 节点和连线正确

### Step 4：运行成功案例（Day 2-3）

每个场景执行 1 次完整成功的 Run。

**操作：**
1. 触发 Agent 执行（或手动上报事件）
2. 等待 Run 完成
3. 检查 Run 列表、详情、Trace 时间线

**检查清单：**
- [ ] Run status = `completed`
- [ ] Trace 时间线显示所有 span，顺序正确
- [ ] ToolCall 记录完整（工具名、参数、结果、耗时）
- [ ] Token 和成本统计正确
- [ ] Artifact 正确关联到 Run

### Step 5：运行失败案例（Day 3-4）

每个场景执行 5 类失败（共 15 个失败案例）。

**操作：**
1. 按第 4 节的方法制造失败
2. 观察平台行为
3. 生成 RCA 和 Runbook
4. 验证 Approval 拦截

**检查清单（每类失败）：**
- [ ] Run status = `failed`
- [ ] Trace 时间线标记了失败 span
- [ ] RCA 生成，引用了有效证据
- [ ] Runbook 生成，步骤可执行
- [ ] 审计日志记录了失败事件

### Step 6：记录观察结果（Day 4-5）

填写第 8 节的反馈表，每个场景一份。

---

## 7. 通过 / 不通过标准

### 通过标准（全部满足）

| # | 条件 |
|---|------|
| P1 | 3 个场景全部完成 Step 1-5 |
| P2 | M1（失败定位时间）≤ 5 分钟 |
| P3 | M4（高风险工具拦截率）= 100% |
| P4 | M5（审计追溯完整率）= 100% |
| P5 | 无阻塞性 Bug（数据丢失、安全漏洞、界面崩溃） |
| P6 | 中文体验评分 ≥ 4/5 |

### 不通过条件（任一满足即不通过）

| # | 条件 |
|---|------|
| F1 | 任意场景无法完成接入（Connector 或 API 报错） |
| F2 | RCA 无法引用任何有效证据（纯泛泛建议） |
| F3 | 高风险工具调用未被 Approval 拦截 |
| F4 | 审计日志丢失关键操作记录 |
| F5 | 中文界面存在大量英文硬编码（覆盖率 < 80%） |

### 有条件通过（需记录改进项）

- 通过主要标准，但存在非阻塞性问题（如文案不准确、布局小问题、性能可接受但不理想）
- 记录为 v3.1 改进项

---

## 8. 反馈表模板

每个试点场景填写一份。

```
场景名称：__________________
验收人员：__________________
验收日期：__________________

## 接入体验

| 项目 | 评分 (1-5) | 备注 |
|------|-----------|------|
| Connector 创建是否顺畅 | | |
| 事件上报是否有足够文档 | | |
| Workflow 创建是否直观 | | |
| DAG 可视化是否有帮助 | | |

## 可观察性

| 项目 | 评分 (1-5) | 备注 |
|------|-----------|------|
| Run 列表信息是否充分 | | |
| Trace 时间线是否清晰 | | |
| 失败时能否快速定位问题 | | |
| Token / 成本统计是否有用 | | |

## RCA & Runbook

| 项目 | 评分 (1-5) | 备注 |
|------|-----------|------|
| RCA 根因是否准确 | | |
| RCA 证据是否有效 | | |
| Runbook 步骤是否可执行 | | |
| Runbook 是否有实际帮助 | | |

## 治理与审批

| 项目 | 评分 (1-5) | 备注 |
|------|-----------|------|
| 高风险工具是否被拦截 | | |
| 审批流程是否顺畅 | | |
| 审计日志是否完整 | | |

## 中文体验

| 项目 | 评分 (1-5) | 备注 |
|------|-----------|------|
| 界面中文覆盖率 | | |
| 术语是否准确易懂 | | |
| 是否有中英文混杂 | | |
| 告警 / 错误信息是否清晰 | | |

## 整体评价

| 项目 | 评分 (1-5) |
|------|-----------|
| 整体满意度 | |
| 是否愿意继续使用 | |
| 是否推荐给其他团队 | |

## 发现的问题

| # | 严重程度 | 描述 | 复现步骤 |
|---|----------|------|----------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

## 改进建议

（自由填写）

```

---

## 9. 试点后决策

验收完成后，根据结果做出以下决策之一：

### 决策 A：进入 v3.1（SSO/OIDC）

**条件：** 通过标准全部满足，反馈表整体满意度 ≥ 4/5。

**下一步：**
- 实施 SSO/OIDC 集成
- 扩大试点范围至更多团队
- 根据反馈表中的改进建议制定 v3.1 backlog

### 决策 B：优先修复体验问题

**条件：** 通过标准基本满足，但存在多个非阻塞性体验问题。

**下一步：**
- 收集所有反馈表中的问题
- 按严重程度排序，优先修复 P0/P1
- 修复后进行第二轮验收（缩小范围，仅验证修复项）
- 第二轮通过后进入 v3.1

### 决策 C：暂停新功能，先增强稳定性

**条件：** 存在不通过条件（F1-F5），或反馈表整体满意度 < 3/5。

**下一步：**
- 停止 v3.1 功能开发
- 聚焦稳定性：Connector 可靠性、RCA 准确性、Approval 拦截率
- 制定稳定性增强计划，明确修复时间线
- 修复后重新验收

---

## 附录：验收时间表

| 天 | 工作内容 | 负责人 |
|----|----------|--------|
| Day 1 | Staging 部署 + 健康检查 | 运维 |
| Day 1-2 | 创建 Connector + 验证连接 | 运维 + 开发 |
| Day 2 | 创建 Workflow + DAG 验证 | 开发 |
| Day 2-3 | 运行成功案例（3 个场景） | 测试 |
| Day 3-4 | 运行失败案例（15 个失败） | 测试 |
| Day 4-5 | 填写反馈表 + 汇总结果 | 全员 |
| Day 5 | 试点决策会议 | 产品 + 工程负责人 |

**总周期：5 个工作日**

---

## 附录：关键 API 速查

| 操作 | API |
|------|-----|
| 健康检查 | `GET /health` |
| 创建 Connector | `POST /api/connectors` |
| 上报事件 | `POST /api/connectors/{id}/events` |
| 创建 Workflow | `POST /api/workflows` |
| 启动 Workflow Run | `POST /api/workflows/{id}/runs` |
| 查看 Run 列表 | `GET /api/runs` |
| 查看 Run 详情 | `GET /api/runs/{id}` |
| 查看 Trace | `GET /api/runs/{id}/trace` |
| 查看待审批 | `GET /api/approvals` |
| 批准 | `POST /api/approvals/{id}/approve` |
| 拒绝 | `POST /api/approvals/{id}/reject` |
| 查看审计日志 | `GET /api/audit-logs` |
| 查看指标 | `GET /api/metrics` |
