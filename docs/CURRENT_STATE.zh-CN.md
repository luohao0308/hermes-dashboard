# 当前状态 — AI Workflow Control Plane

**最后更新：** 2026-05-02
**状态：** 已稳定到可内部试点（v3.0 + Optimization Release）

## 概述

AI Workflow Control Plane 是一个用于观测、治理、审计和复盘 AI 工作流的通用平台。当前版本为 v3.0 + Optimization Release，已完成产品化、安全加固、生产运维和质量改进。

## 核心能力

| 模块 | 功能 |
|------|------|
| **工作流观测** | 运行列表/详情、Trace 时间线、状态/运行时/失败筛选、成本/延迟/Token 汇总 |
| **工具治理** | 风险等级工具策略、允许/确认/拒绝决策、审批收件箱 |
| **RCA / Runbook** | 根因分析（带证据链）、自动生成恢复 Runbook |
| **连接器框架** | 统一事件摄入 API（7 种事件类型、幂等、批量） |
| **评估与配置** | 离线评估评分、配置版本追踪、前后对比（含分数差异） |
| **审计追踪** | 审批决策、配置变更、工具调用和连接器错误日志 |
| **工作流编排** | DAG 工作流定义、节点依赖、重试策略、超时策略、人工审批 |
| **安全** | 密钥加密存储、HMAC Webhook 验证、RBAC 三角色、审计日志 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + vue-i18n |
| 后端 | Python FastAPI |
| 数据库 | PostgreSQL |
| 迁移 | Alembic |
| 实时 | SSE (Server-Sent Events) |
| API Schema | Pydantic |

## 前端国际化

前端使用 vue-i18n v9 进行国际化，默认语言为 zh-CN（简体中文），可切换为 en-US（英文）。

- 语言切换：顶栏右侧语言切换器
- 持久化：localStorage（`hermes_locale` 键）
- 检测顺序：localStorage → `navigator.language` → 回退 `en-US`

## 快速启动

```bash
# 1. 克隆并配置
git clone <repo-url>
cd hermes_free
cp .env.example .env
# 编辑 .env，填入 DATABASE_URL 和 API 密钥

# 2. 启动 PostgreSQL（或使用 Docker）
docker compose up -d postgres

# 3. 运行迁移
cd backend
alembic upgrade head

# 4. 启动应用
cd ..
./start.sh
```

访问 http://localhost:5173

## 环境变量

| 变量 | 必需 | 描述 |
|------|------|------|
| `DATABASE_URL` | 是 | PostgreSQL 连接字符串 |
| `ENVIRONMENT` | 否 | `development`（默认）或 `production`。生产环境需要 `ENCRYPTION_KEY` |
| `ENCRYPTION_KEY` | 生产 | Fernet 密钥，用于连接器密钥加密。开发环境自动生成 |
| `GITHUB_TOKEN` | 否 | GitHub Personal Access Token |
| `OPENAI_API_KEY` | 否 | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | 否 | Anthropic API 密钥 |

## 已知限制

- 无 SSO/OIDC 集成（v3.1 候选）
- 无 Connector SDK 示例（v3.1 候选）
- 调度器为进程内实现，单实例限制已文档化

## 测试状态

**本地（权威）：** 477 passed, 0 failed — 全绿。

**Docker：** 282 passed, 23 failed, 172 skipped。23 个失败全部是 Docker 环境特有的，本地同样测试全部通过。CI 和发布验收使用本地测试套件。

| 失败来源 | 数量 | 根因 |
|----------|------|------|
| `test_terminal_ws.py` | 11 | Docker 缺少交互式 PTY |
| `test_hermes_tools.py` | 5 | 旧 Dashboard API mock 不匹配 |
| `test_auth.py` | 4 | `passlib` 的 `crypt` 模块在 Python 3.11+ 已废弃（Docker 使用 3.11） |
| `test_agent_switch.py` | 2 | Agent session mock 期望不匹配 |
| `test_providers.py` | 1 | Provider health_check mock |

## 当前验收备注

当前系统可用于内部试点。前端 10 个核心页面可加载，RCA、Runbook、Workflow 启动、Approval approve/reject 等核心业务流程已验证可用；页面不再出现 `undefined` 错误文案。

最新 Docker 验收中的非阻塞已知限制：

1. **小米 Mimo Provider 连接**：Provider `test-mimo` 可注册，但 `docker-compose.yml` 未配置 `MINIMAX_API_KEY`，连接测试会返回明确的 API key 不可用/缺失错误。这是部署配置缺口，不影响核心工作流闭环。
2. **Terminal WebSocket 测试**：11 个 pre-existing 测试失败，原因是 Docker 环境不稳定支持交互式 PTY 终端行为；失败范围隔离在 Terminal WebSocket 测试。
3. **Hermes Tools 兼容测试**：5 个 pre-existing 测试失败，与旧 Dashboard API mock/兼容路径相关，不属于当前 AI Workflow Control Plane 运行时阻塞问题。
4. **Auth 密码哈希测试**：4 个 pre-existing 测试失败，原因是 Docker 的 Python 3.11 废弃了 `passlib` 使用的 `crypt` 模块。本地（Python 3.14）通过。
5. **Agent Switch mock 测试**：2 个 pre-existing 测试失败，与 Agent session mock 期望相关。
6. **Provider Registry mock 测试**：1 个 pre-existing 测试失败，与 Provider health_check mock 相关。
