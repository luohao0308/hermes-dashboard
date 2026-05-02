# Platform Optimization Execution Plan

## 目标

在 v3 release-ready 基础上，对 AI Workflow Control Plane 做产品化整合、架构收束、生产化和安全闭环优化。

本计划不重新定义产品方向，不新增大而散的功能。它专注于现有能力的整合和可交付性。

## 执行原则

- 先收束，再扩展。
- 旧功能先标记 Legacy，再逐步迁移，不直接硬删。
- 所有新主线围绕 Runtime、Run、TraceSpan、ToolCall、Approval、Artifact、Workflow、Eval。
- 文档和代码同步推进，避免后续 AI 误判项目状态。
- 每个阶段都必须保留现有测试通过。

## Phase 0：文档与事实源收束

| ID | 任务 | 优先级 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|
| OPT-00 | 新增优化文档 | P0 | 创建 `PRODUCT_OPTIMIZATION_OVERVIEW.md` 和本文件 | 两份文档存在且分别面向人和 AI |
| OPT-01 | 重写当前架构文档 | P0 | 用 v3 控制面架构替换旧 Hermès 架构 | `ARCHITECTURE.md` 不再以 Hermès Bridge 为中心 |
| OPT-02 | 重写运维文档 | P0 | 覆盖 PostgreSQL、Alembic、workers、production env、backup/restore | `OPERATIONS.md` 可指导本地和生产运维 |
| OPT-03 | 重写发布检查清单 | P0 | 增加 auth、RBAC、secret、webhook、worker、migration 检查 | `CHECKLIST.md` 反映 v3 平台状态 |
| OPT-04 | 增加生产部署文档 | P1 | 创建 `PRODUCTION_DEPLOYMENT.md` | 能从空机器部署 web、DB、workers |
| OPT-05 | 归档旧图和旧 release 汇总 | P1 | 将旧 `architecture-diagram.html` 和旧汇总 release notes 移到 `docs/archive/legacy/` | 当前 docs 根目录无误导旧图 |
| OPT-06 | 文档一致性检查 | P1 | 对 README、CURRENT_STATE、ARCHITECTURE、API_CONTRACT 进行关键词检查 | 旧主定位只出现在 archive 或 legacy adapter |

## Phase 1：前端产品体验整合

| ID | 任务 | 优先级 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|
| OPT-10 | 重组导航信息架构 | P0 | 将导航分为 Observe、Govern、Improve、Integrate、Admin、Legacy | 新用户能按业务目标找到功能 |
| OPT-11 | 品牌统一 | P0 | Sidebar 从 Code Review 改为 AI Control Plane；移除 CR logo 文案 | 主 UI 不再表达旧代码审查定位 |
| OPT-12 | Legacy 分组 | P0 | Code Review、Agent Chat、Terminal、旧 History 放入 Legacy | 旧功能可用但不抢主线 |
| OPT-13 | 拆分 App.vue | P0 | 拆出 route config、page shell、workflow state composables | `App.vue` 明显减负，测试通过 |
| OPT-14 | 统一页面状态组件 | P1 | 新增 LoadingState、EmptyState、ErrorState、UnauthorizedState | Runs/Workflows/Approvals/Evals 共用状态组件 |
| OPT-15 | 统一详情页框架 | P1 | Header metrics、Timeline、Artifacts、Audit、Actions 统一布局 | RunDetail/WorkflowDetail/RCA 页面视觉一致 |
| OPT-16 | 前端主线 smoke test | P1 | 增加导航和核心页面渲染测试 | `npm run test:unit` 通过 |

## Phase 2：后端架构收束

| ID | 任务 | 优先级 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|
| OPT-20 | 拆分 legacy routers | P0 | 将 `main.py` 内旧 `/api/agent/*`、`/api/sessions/*`、`/tasks` 移入 legacy router | 新 API 和 legacy API 边界清晰 |
| OPT-21 | Deprecation header | P0 | legacy API 返回 `Deprecation: true` 和 `Link` 到替代 API 文档 | 客户端可识别旧接口 |
| OPT-22 | 旧桥接能力 connector 化 | P1 | 将 Hermès proxy、GitHub review、Agent chat 作为 connector/legacy adapter 记录 | 当前架构不以旧系统为中心 |
| OPT-23 | SQLite fallback 收束 | P1 | 文档和代码标明只读兼容；禁止新写入 SQLite | 新功能只写 PostgreSQL |
| OPT-24 | Service 层提取 | P1 | 优先从 workflows、connectors、run_analysis 开始提取 service | router 中业务复杂度下降 |
| OPT-25 | 后端兼容测试 | P1 | legacy API 行为不破坏，新 API 测试仍通过 | 后端测试通过 |

## Phase 3：安全与权限闭环

| ID | 任务 | 优先级 | 状态 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|---|
| OPT-30 | Auth MVP | P0 | Done | 实现本地用户登录、session 或 JWT，保留 header role 仅 dev/test | 生产不依赖裸 `X-User-Role` |
| OPT-31 | 全写 API RBAC | P0 | Done | 所有 POST/PUT/PATCH/DELETE endpoint 增加 RBAC helper | viewer 写操作全部被拒绝 |
| OPT-32 | Service token | P0 | Done | 增加 connector ingestion 和 worker 内部 API token | 机器调用不冒充用户 |
| OPT-33 | Rate limiting | P1 | Done | connector、auth、RCA、Runbook、Eval 增加限流策略 | 高成本 endpoint 有保护 |
| OPT-34 | Audit UI | P1 | Done | 管理员可按 actor/resource/action/time 查询 audit log | 审计不只在数据库里 |
| OPT-35 | Secret leak tests | P1 | Done | 响应、日志、audit、错误路径中验证无明文 secret | 安全测试通过 |

## Phase 4：生产化与运维

| ID | 任务 | 优先级 | 状态 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|---|
| OPT-40 | Production deployment guide | P0 | Done | 完成 `PRODUCTION_DEPLOYMENT.md` | 可启动 web、scheduler、retention、PostgreSQL |
| OPT-41 | Health check matrix | P0 | Done | API、DB、worker、retention、connector ingestion 状态可查 | 运维能判断系统健康 |
| OPT-42 | Structured logging | P1 | Done | 增加 request_id、run_id、workflow_id、actor_id 日志字段 | 排错可串联请求 |
| OPT-43 | Metrics endpoint | P1 | Done | 暴露基础指标：runs、worker lag、approval pending、connector errors | 可接 Prometheus 或外部采集 |
| OPT-44 | Backup/restore runbook | P1 | Done | PostgreSQL backup、restore、migration rollback 文档和演练步骤 | 数据恢复路径明确 |
| OPT-45 | CI matrix | P1 | Done | Python 3.9、frontend、backend PG、Alembic empty DB | CI 覆盖当前真实风险 |

## Phase 5：现有核心能力增强

| ID | 任务 | 优先级 | 状态 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|---|
| OPT-50 | Cursor pagination | P1 | Done | Runs、Approvals、Audit 支持 cursor（保留 offset 兼容） | 大数据翻页稳定 |
| OPT-51 | Saved filters | P1 | Done | localStorage 版本，按 namespace 隔离，strips sensitive fields | 重复排查效率提升 |
| OPT-51b | Audit UI enhancement | P1 | Done | 快捷筛选 chips、resource_id 搜索、JSON/CSV 导出 | 审计排错效率提升 |
| OPT-52 | Workflow rollback | P2 | Done | Workflow definition 支持回滚到历史版本 | 错误配置可恢复 |
| OPT-53 | Connector SDK examples | P2 | | Python/Node 示例，含签名生成和批量事件 | 外部接入成本下降 |
| OPT-54 | Event replay | P2 | Done | 失败 connector event 可重放 | 接入排错更可靠 |
| OPT-55 | Approval batch actions | P2 | Done | 批量 approve/reject，支持 reason template | 审批效率提升 |
| OPT-56 | RCA evidence score | P2 | | RCA 显示证据质量和低置信度原因 | 避免过度信任低质量 RCA |
| OPT-57 | Eval recommendation guardrail | P2 | Done | 推荐配置需要 approval 才能应用 | 优化不绕过治理 |
| OPT-58 | Connector events cursor pagination | P2 | Done | Failed events 支持 cursor（保留 offset 兼容） | 大数据翻页稳定 |
| OPT-59 | Scheduler single-instance protection | P2 | Done | Heartbeat 含 worker_id/PID；advisory lock 文档化 | 多实例安全可观测 |

## Phase 6：文档减法和长期维护

| ID | 任务 | 优先级 | 具体步骤 | 验收标准 |
|---|---|---:|---|---|
| OPT-60 | 单一当前事实源 | P0 | Done | `CURRENT_STATE.md`、`ARCHITECTUREURE.md`、README 保持同步，release notes 创建 | 三者不冲突 |
| OPT-61 | 历史文档归档规则 | P0 | 旧方向、旧计划、旧图统一入 archive | 根目录 docs 只保留当前文档 |
| OPT-62 | 模块文档索引 | P1 | 每个核心模块只保留一份当前文档 | AI 不再被重复文档误导 |
| OPT-63 | Release notes 策略 | P1 | v1/v2/v3 release notes 保留，旧汇总归档 | 版本历史清晰 |

## Optimization Release Status

**Phases 0–5 complete.** All P0 and P1 tasks done. P2 tasks OPT-52/54/55/57/58/59 done. OPT-53 and OPT-56 deferred (low risk).

See `docs/OPTIMIZATION_RELEASE_NOTES.md` for full details and verification results.

## v3.1 Candidates (Not Current Release)

These items are tracked for a future v3.1 release. They are NOT blockers for the current Optimization Release:

| Item | Priority | Notes |
|------|----------|-------|
| SSO/OIDC | P0 | Design doc exists (`docs/SSO_OIDC_DESIGN.md`). Requires IdP integration decisions. |
| Connector SDK examples | P2 | Python/Node examples with signature generation (OPT-53) |
| RCA evidence score | P2 | Quality indicator for root cause analysis (OPT-56) |
| Phase 6 doc maintenance | P1 | OPT-61/62/63: archive rules, module doc index, release notes strategy |

## 测试要求

### Frontend

```bash
cd frontend
npx vue-tsc --noEmit
npm run test:unit
npm run build
```

新增测试：

- Sidebar 分组渲染。
- Legacy 分组可见但不作为主入口。
- Unauthorized / Empty / Error 状态组件。
- RunDetail / WorkflowDetail 关键状态不回归。

### Backend

```bash
cd backend
python -m pytest tests/ -v
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test python -m pytest tests/ -v
alembic upgrade head
```

新增测试：

- viewer 写操作拒绝。
- operator/admin 权限边界。
- legacy endpoint 带 deprecation header。
- production 缺少 ENCRYPTION_KEY 启动失败。
- worker health 和 DB health。

### 文档

```bash
rg -n "Hermès Dashboard|Hermes Dashboard|Code Review Pipeline|Bridge Server" docs README.md frontend/src backend -g '!docs/archive/**'
```

验收标准：

- 旧主定位只允许出现在 archive、legacy adapter 或兼容说明中。
- 当前文档统一称为 AI Workflow Control Plane。

## 风险和缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 一次性拆 `App.vue` 导致前端回归 | 高 | 先拆 route config 和状态 composable，逐页迁移 |
| 一次性拆 `main.py` 破坏旧 API | 高 | 先建立 legacy router 和 deprecation header，再迁移实现 |
| Auth MVP 影响开发便利性 | 中 | dev/test 支持 header override，production 禁止 |
| 文档再次膨胀 | 中 | 当前文档保留，探索文档归档 |
| Production 部署差异 | 中 | Docker Compose staging 演练和 checklist |

## 完成定义

本优化计划第一阶段完成时，应满足：

- 当前 docs 根目录没有误导性的旧架构文档。
- 产品导航按 Observe/Govern/Improve/Integrate/Admin/Legacy 组织。
- 主品牌是 AI Control Plane。
- 新 API 和 legacy API 边界明确。
- 所有写 API 有权限策略计划和测试清单。
- 生产部署、备份恢复、worker topology 有文档。
- 后续 AI 可以直接按本文件继续执行，不需要重新判断方向。

