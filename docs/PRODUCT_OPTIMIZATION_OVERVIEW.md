# Product Optimization Overview

## 一句话结论

AI Workflow Control Plane 已经完成 v0-v3 主线。下一阶段的核心不是继续堆功能，而是把现有能力整合成一个真正可交付、可运营、可扩展的平台。

## 当前位置

项目已经具备：

- Workflow Observability：Runs、Trace Timeline、成本、延迟、token 汇总。
- Tool Governance：工具风险等级、Approval Inbox、审批审计。
- RCA / Runbook：失败复盘、证据链、处理步骤、Markdown artifact。
- Connector Framework：外部 runtime 通过统一事件协议接入。
- Eval / Config Optimization：评估结果、配置版本、配置对比。
- Workflow Orchestration：DAG workflow、task、retry、timeout、approval node。
- Durable Execution：worker、锁、backoff、dead letter、状态恢复。
- Enterprise Foundation：secret encryption、webhook signature、RBAC、audit、users/teams/environments、retention。

这些能力已经让项目从旧的单点 Dashboard 变成通用控制面。但从 CEO/产品负责人视角看，当前还不是“可放心交给团队长期使用”的状态。

## 当前真实痛点

### 1. 产品入口还像功能堆叠

导航里同时存在 Runs、Workflows、Approvals、Eval、旧 Code Review、旧 Agent Chat、Terminal、History、System。用户能看到很多功能，但不容易理解优先路径。

下一阶段要让用户第一眼明白：

```text
Observe -> Govern -> Improve -> Integrate -> Admin
```

也就是先观察运行，再治理风险，再复盘优化，再接入系统，最后做管理。

### 2. 旧叙事仍然影响体验

部分前端文案、CSS 注释、旧文档仍保留 Code Review、Hermès、Agent 专属语义。它们不应再作为主线出现，只能作为 legacy adapter 或 connector 示例。

### 3. 架构实现已经强大，但边界不清

`backend/main.py` 和 `frontend/src/App.vue` 都承担了过多职责。新控制面 API、旧兼容 API、旧 Agent Chat、旧 session proxy 混在一起，后续 AI 很容易误判主线。

### 4. 安全还是“企业底座”，不是完整产品

当前 RBAC 仍使用 `X-User-Role` header 作为占位。它适合开发阶段和测试，但不适合生产。下一阶段要落地本地认证、service token 和后续 OIDC。

### 5. 运维交付还不完整

项目有 Docker、PostgreSQL、Alembic、worker、retention，但缺少完整生产部署文档、备份恢复、健康检查矩阵、worker topology、observability 和 migration 演练。

### 6. 文档数量多，但缺少“当前唯一事实源”

现在文档很多，历史文档也很多。下一阶段要减少误导：当前架构、当前 API、当前部署、当前限制必须一眼可见；历史探索统一归档。

## 下一阶段目标

把项目从“功能齐全的工程原型”升级为“可运营的 AI Workflow Control Plane”。

成功后的表现：

- 新用户 3 分钟内能理解平台主导航和核心价值。
- 新 AI 接手不会回到旧 Hermès / Code Review / 单 Agent 叙事。
- 前端页面按业务心智分组，而不是按开发历史堆叠。
- 后端新 API 与 legacy API 边界清晰。
- 生产环境能明确启动 web、scheduler worker、retention worker、PostgreSQL。
- 所有写操作有清晰权限策略、审计和测试。
- 文档能指导部署、排错、升级和后续开发。

## 优先级判断

| 优先级 | 方向 | 为什么 |
|---|---|---|
| P0 | 文档与信息架构收束 | 防止后续 AI 和工程师继续在旧叙事里开发 |
| P0 | 前端导航和品牌统一 | 这是用户感知最强的混乱点 |
| P0 | 后端 legacy 边界 | 这是架构维护最大风险 |
| P0 | RBAC 覆盖所有写 API | 当前安全能力必须从“有模型”变成“有保护” |
| P1 | 生产部署和健康检查 | 平台要能被真实运行和维护 |
| P1 | Audit UI 和 Cursor Pagination | 数据量上来后必须可查、可翻、可导出 |
| P2 | OIDC、Connector SDK、OpenTelemetry | 重要，但应在产品化基线稳定后推进 |

## 不做什么

下一阶段不优先做：

- 大规模重写前后端。
- 新增更多独立大功能。
- 引入 Temporal/Hatchet 等重型编排系统。
- 一次性实现完整 SSO/OIDC。
- 直接删除旧功能导致兼容破坏。

旧功能应先进入 Legacy 分组和兼容 adapter，等新主线稳定后再逐步退场。

## CEO 视角的产品路线

### Step 1：让产品看起来像一个产品

重组导航、统一品牌、统一页面状态、统一详情页布局，让平台第一屏就表达“控制面”。

### Step 2：让架构边界可维护

拆出 legacy API 和 legacy UI，保留兼容但降低其主线权重。

### Step 3：让安全从占位变成真实闭环

落地本地 auth、service token、全写 API RBAC、audit UI。

### Step 4：让运维可交付

补生产部署、备份恢复、worker topology、health check、metrics。

### Step 5：增强现有核心能力

围绕 Runs、Workflows、Connectors、Approvals、RCA、Eval 做小而稳的增强，不做方向漂移。

## 推荐下一步

先执行 `docs/PLATFORM_OPTIMIZATION_EXECUTION_PLAN.md` 的 Phase 0 和 Phase 1：

1. 完成文档基线。
2. 重组前端导航。
3. 统一品牌和主线文案。
4. 给旧页面打 Legacy 标识。

这一步完成后，用户会明显感觉“这是一个平台”，而不是“很多功能页的集合”。

