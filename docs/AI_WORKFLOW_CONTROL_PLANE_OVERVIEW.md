# AI Workflow Control Plane Overview

## 一句话定位

一个通用 AI Workflow Control Plane，用于观察、治理、审计和复盘 AI 工作流。

它面向多模型、多工具、多运行时、多 Agent 或非 Agent 自动化流程，不绑定某一个特定 Dashboard、框架或单一执行体。平台核心不是“一个 Agent”，而是一次 AI 工作流从输入、执行、工具调用、人工审批、失败复盘到持续优化的完整生命周期。

## 为什么要做

AI 工作流正在从简单聊天变成复杂自动化系统：

- 多 Agent、多模型、多工具调用难以追踪，失败后很难还原决策链路。
- 长任务和异步任务越来越多，用户需要知道任务当前卡在哪里。
- 工具调用风险变高，尤其是写文件、执行命令、访问网络、触发部署等动作。
- 失败原因不透明，排查依赖人工翻日志、猜测模型行为和复现上下文。
- 成本、延迟、Prompt 效果和配置变更缺少统一评估依据。
- 不同 Runtime 各有自己的事件格式，团队缺少一个统一的控制面。

这个项目要解决的是：让 AI 工作流变得可见、可审计、可治理、可复盘、可改进。

## 它不是什么

- 不是特定系统的专属 Dashboard。
- 不是单 Agent 聊天应用。
- 不是替代 OpenAI Agents SDK、LangGraph、CrewAI、AutoGen 或自研 Runtime 的框架。
- 不是一开始就做完整自动执行平台。
- 不是只服务代码审查，代码审查只是其中一个可接入的工作流类型。

## 目标用户

- AI 应用开发者：需要调试模型调用、工具调用和长任务执行。
- AgentOps / 平台工程团队：需要观察、治理和审计多个 AI Runtime。
- 自动化与 DevOps 团队：需要控制高风险工具调用和修复流程。
- 产品与业务团队：需要理解 AI 工作流为什么失败，以及改动是否真的变好。
- 安全与合规团队：需要审批记录、审计日志和风险分级。

## 核心对象

| 对象 | 含义 |
|---|---|
| Runtime | 外部 AI 运行时或自动化系统，例如 Agents SDK、自研 Agent、CI/CD、代码审查流水线 |
| Run | 一次完整 AI 工作流运行 |
| Task | Run 内部的可调度任务单元 |
| TraceSpan | 一次可观察行为，例如模型调用、工具调用、handoff、审批、错误 |
| ToolCall | 工具调用记录，包含风险等级、输入、输出、状态和治理决策 |
| Approval | 人工审批事件，用于控制高风险动作 |
| Artifact | 工作流产物，例如报告、日志片段、代码 diff、RCA、Runbook、Markdown 导出 |
| EvalResult | 模型、Prompt、Agent 配置或工具策略的评估结果 |

## 核心能力

| 能力 | 说明 |
|---|---|
| Workflow Observability | 展示 Run 列表、Run 详情、Trace Timeline、错误节点、耗时、token 和成本 |
| Tool Governance | 对工具调用做风险分级、allow/confirm/deny 决策和审批记录 |
| Failure Review | 对失败 Run 生成 RCA，引用 trace、日志或 tool call 作为证据 |
| Runbook Automation | 从 RCA 生成可执行检查步骤，并将高风险步骤纳入审批 |
| Connector Framework | 允许多个 Runtime 通过统一事件 API 写入 Run、Trace、Artifact |
| Eval & Optimization | 对模型、Prompt、Agent 配置和工具策略做效果比较 |
| Auditability | 保存审批、配置变更、工具调用和关键状态变更的审计日志 |

## 分版本路线

| 版本 | 名称 | 目标 |
|---|---|---|
| v0.1 | 文档与产品定位重构 | 从旧叙事解耦，明确通用 AI Workflow Control Plane 主线 |
| v0.2 | PostgreSQL 基础设施 | 建立生产级主数据库、migration 和通用 schema |
| v1.0 | Workflow Observability MVP | 完成 Run、Trace、ToolCall、Artifact 的基础观察能力 |
| v1.1 | Tool Governance | 完成工具风险治理、审批流和审计记录 |
| v1.2 | RCA / Runbook | 完成失败复盘、证据链和处理方案生成 |
| v1.3 | Connector Framework | 支持不同 Runtime 接入同一控制面 |
| v1.4 | Eval / Config Optimization | 支持配置效果比较和持续优化 |
| v1.5 | Stabilization / Release Hardening | 文档、测试、导航、兼容路径一致性 |
| v2.0 | Workflow Orchestration | 增加 Task DAG、条件路由、重试、超时和人工节点 |
| v2.1 | Durable Execution | 支持更可靠的长任务执行和 worker 恢复 |
| v3.0 | Enterprise Features | 增加团队权限、密钥治理、多环境、签名校验和保留策略 |

## 当前最优先做什么

```text
v1 已完成：观察、治理、复盘、连接、评估全链路。
下一步进入 v2 Workflow Orchestration：Task DAG、条件路由、重试和超时。
```

## 当前进度总览

| 模块 | 当前进度 |
|---|---:|
| 产品定位 | 100% |
| PostgreSQL 基础设施 | 100% |
| Run / Trace 观察能力 | 100% |
| Tool Governance | 100% |
| RCA / Runbook | 100% |
| Connector Framework | 100% |
| Eval / Config | 100% |
| Stabilization | 100% |

## 落地原则

- 先做观察、治理、复盘，再做完整自动执行。
- PostgreSQL 是主数据库，SQLite 只能作为本地临时 fallback，不能作为生产设计目标。
- Runtime、Run、Task、TraceSpan、ToolCall、Approval、Artifact 是核心抽象。
- Connector 负责接入外部系统，核心 UI 和核心 API 不依赖某个特定 Runtime。
- 高风险工具调用必须可拦截、可审批、可审计。
- RCA 和 Runbook 必须引用证据，避免空泛建议。

