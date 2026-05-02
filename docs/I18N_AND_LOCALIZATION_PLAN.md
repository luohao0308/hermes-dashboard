# i18n & Localization Plan

## Overview

The AI Workflow Control Plane frontend uses **vue-i18n v9** for internationalization. The default locale is `zh-CN` (Chinese Simplified), with `en-US` (English) as a switchable alternative.

## Architecture

- **Library**: vue-i18n v9, Composition API mode (`legacy: false`)
- **Locale files**: `frontend/src/i18n/zh-CN.ts` and `frontend/src/i18n/en-US.ts`
- **Instance setup**: `frontend/src/i18n/index.ts` — creates i18n instance, detects locale, exports `setLocale()`/`getLocale()`
- **Persistence**: `localStorage` key `hermes_locale`
- **Detection order**: localStorage → `navigator.language` → fallback `en-US`

## Locale File Structure

Both locale files use identical key structure, organized by feature area:

```
common.*       — shared UI strings (buttons, status, labels)
nav.*          — navigation item labels
navGroup.*     — navigation group labels
sidebar.*      — sidebar component
topbar.*       — top bar component
dashboard.*    — dashboard page
runs.*         — run list/detail
runDetail.*    — run detail page
workflows.*    — workflow list/detail
approvals.*    — approval inbox
audit.*        — audit log
evals.*        — eval dashboard
configCompare.* — config diff page
connectors.*   — connector management
health.*       — health matrix
trace.*        — trace timeline
session.*      — session detail (heaviest)
alerts.*       — alerts panel
knowledge.*    — knowledge base
cost.*         — cost tracking
guardrails.*   — tool policies
agentOps.*     — agent ops overview
status.*       — status labels
terminal.*     — terminal
toast.*        — toast notification messages
errors.*       — error messages
```

## Terminology Table

| English | zh-CN | Notes |
|---------|-------|-------|
| Runtime | 运行时 | |
| Run | 运行记录 | |
| Workflow | 工作流 | |
| Trace | 追踪 | |
| TraceSpan | 追踪片段 | |
| ToolCall | 工具调用 | |
| Approval | 审批 | |
| Artifact | 产物 | |
| Eval | 评估 | |
| Audit | 审计 | |
| Connector | 连接器 | |
| Environment | 环境 | |
| Retention | 保留策略 | |
| Root Cause Analysis | 根因分析 | |
| Runbook | Runbook | Kept in English |
| DAG | DAG | Kept in English |
| Token | Token | Kept in English |

## Adding New Strings

1. Add the key to both `zh-CN.ts` and `en-US.ts` under the appropriate section
2. Use `useI18n()` in `<script setup>` and `t('section.key')` in templates
3. For interpolation: `t('key', { variable: value })` with `{variable}` in the message
4. Run `vue-tsc --noEmit` to verify type safety
5. Run `npm run test:unit` to verify tests pass

## Test Setup

Tests use `setup.ts` which registers vue-i18n globally and forces `en-US` locale:

```typescript
import { config } from '@vue/test-utils'
import i18n from '../src/i18n'
i18n.global.locale.value = 'en-US'
config.global.plugins = [i18n]
```

When adding tests, assert against English text (en-US translations).

## Migration Status

### Fully Migrated (use `t()` for all user-visible text)

| Component | Notes |
|-----------|-------|
| Sidebar.vue | Nav groups, items, status |
| TopBar.vue | Gateway status, refresh, language switcher |
| App.vue | Toast messages, status bar, quick actions |
| RunList.vue | Header, filters, pagination |
| RunDetail.vue | All labels, sections |
| ApprovalInbox.vue | Header, filters, batch actions |
| AuditLogPanel.vue | Filters, action options, placeholders, CSV headers, pagination |
| EvalDashboard.vue | Summary cards, trend chart, breakdown tables |
| ConfigCompare.vue | Score delta, badges, notice, changes, version details, empty state |
| WorkflowList.vue | Header, empty state |
| WorkflowDetail.vue | Sections, buttons |
| FailedEventsPanel.vue | Header, actions |
| HealthMatrix.vue | Status labels |
| TraceTimeline.vue | Labels, span details |
| SessionDetail.vue | All sections (heaviest component, ~100 keys) |
| AlertsPanel.vue | Alert cards, severity labels, actions |
| EmptyState.vue | Uses prop-driven text (no hardcoded strings) |
| ErrorState.vue | Retry button |
| UnauthorizedState.vue | Default message |

### i18n Backlog (not yet migrated)

| Component | Est. Strings | Priority | Notes |
|-----------|-------------|----------|-------|
| SystemConfigPanel.vue | ~15 | Medium | System configuration page |
| AgentOpsOverview.vue | ~10 | Low | Agent ops overview dashboard |
| CostDashboard.vue | ~10 | Low | Cost tracking dashboard |
| GuardrailsPanel.vue | ~10 | Low | Tool policy management |
| HistoryList.vue | ~10 | Low | History list (legacy) |
| KnowledgeSearch.vue | ~5 | Low | Knowledge base search |
| LogStream.vue | ~5 | Low | Log stream (legacy) |
| TaskPanel.vue | ~10 | Low | Task panel (legacy) |
| Terminal.vue | ~3 | Low | Terminal emulator (minimal text) |
| AgentChat.vue | ~15 | Low | Legacy chat interface |
| AgentPanel.vue | ~10 | Low | Legacy agent panel |
| ReviewDashboard.vue | ~10 | Low | Legacy code review |
| ProviderPanel.vue | ~10 | Low | Legacy provider management |

Total estimated remaining: ~123 strings across 13 components (all low/medium priority legacy or dashboard pages).

## Backend Error Code Strategy (Future)

Backend returns stable error codes:

```json
{ "error_code": "CONNECTOR_NOT_FOUND", "detail": "..." }
```

Frontend maps error codes to localized messages via toast handlers. This avoids bulk Chinese hardcoding in the backend.
