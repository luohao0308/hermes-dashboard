# Hermès 工作状态监控 Web 网站

## 目标

开发一个 Web 界面，用于实时监控 Hermès Agent 的工作状态，让用户能够直观地看到 Hermès 正在执行的任务、已完成的任务列表、以及实时的日志/输出。

## 与 Obsidian Workspace 联动

- **项目目录**：`~/Desktop/hermes_workspace/hermes_free/`
- **Obsidian Vault**：`~/Documents/Obsidian Vault/`
- **联动方式**：项目文档同步到 Obsidian Vault，使用 wikilinks 双向关联

## 技术方案

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Vite | 渐进式 SPA，简单易用 |
| UI 组件 | TailwindCSS + Naive UI | 美观且轻量 |
| 实时通信 | Server-Sent Events (SSE) | 简单可靠，后端推流 |
| 后端桥接 | Python FastAPI | 轻量 ASGI 服务，连接 Hermès |
| 日志存储 | SQLite (可选) | 持久化任务历史 |

### 目录结构

```
hermes_free/
├── README.md              # 项目总文档
├── backend/
│   ├── main.py           # FastAPI 入口，连接 Hermès
│   ├── sse_manager.py    # SSE 连接管理
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── components/
│   │       ├── TaskPanel.vue
│   │       ├── LogStream.vue
│   │       └── HistoryList.vue
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/
│   ├── backend/
│   │   └── test_sse.py
│   └── frontend/
│       └── test_components.spec.ts
└── docs/
    └── ARCHITECTURE.md
```

## 团队协作流程

### 角色分工

| 角色 | GitHub Account | 职责 |
|------|---------------|------|
| **全栈工程师 (Engineer)** | @luohao | 实现功能代码，每步完成后提交 PR |
| **测试 (QA)** | @hermes-qa | 验证每一步的正确性，执行测试 |
| **领导 (Lead)** | @hermes-lead | 审核代码风格和质量，最终批准 PR |

### GitHub 分支策略

```
main (保护分支)
├── feature/backend-sse (Phase 1.1)
├── feature/frontend-scaffold (Phase 1.2)
├── feature/task-panel (Phase 2.1)
├── feature/log-stream (Phase 2.2)
├── feature/history-list (Phase 2.3)
├── feature/hermes-integration (Phase 3.1)
└── feature/ui-optimization (Phase 3.2)
```

### 工作流程 (每步骤)

```
1. Engineer 创建分支 → 实现功能
2. Engineer 提交 PR 到 main
3. QA 执行测试 → PR 评论测试结果
4. Lead 审核代码 → PR 评论审核结果
5. 通过 → Merge 到 main
6. 失败 → Engineer 修复 → 重复步骤 3-5
```

## 实施步骤

### Phase 1: 基础架构

#### Task 1.1: 搭建后端桥接服务
- **分支**: `feature/backend-sse`
- **文件**:
  - `backend/main.py` - FastAPI 入口
  - `backend/sse_manager.py` - SSE 连接管理
  - `backend/requirements.txt` - Python 依赖
- **测试验证**:
  ```bash
  pytest tests/backend/test_sse.py -v
  curl -N http://localhost:8000/sse
  ```

#### Task 1.2: 搭建前端骨架
- **分支**: `feature/frontend-scaffold`
- **文件**:
  - `frontend/` - Vue 3 + Vite 项目完整结构
  - `frontend/src/App.vue`
  - `frontend/src/main.ts`
  - `frontend/index.html`
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/tsconfig.json`
  - `frontend/tailwind.config.js`
- **测试验证**:
  ```bash
  cd frontend && npm install
  npm run dev
  # 访问 http://localhost:5173
  ```

### Phase 2: 核心功能

#### Task 2.1: 任务状态面板
- **分支**: `feature/task-panel`
- **文件**: `frontend/src/components/TaskPanel.vue`
- **测试验证**: `vitest tests/frontend/test_task_panel.spec.ts`

#### Task 2.2: 实时日志流
- **分支**: `feature/log-stream`
- **文件**: `frontend/src/components/LogStream.vue`
- **测试验证**: `vitest tests/frontend/test_log_stream.spec.ts`

#### Task 2.3: 历史任务列表
- **分支**: `feature/history-list`
- **文件**: `frontend/src/components/HistoryList.vue`
- **测试验证**: `vitest tests/frontend/test_history_list.spec.ts`

### Phase 3: 集成与美化

#### Task 3.1: 接入真实 Hermès 数据源
- **分支**: `feature/hermes-integration`
- **测试验证**: 端到端测试通过

#### Task 3.2: UI/UX 优化
- **分支**: `feature/ui-optimization`
- **测试验证**: Playwright E2E 测试通过

## GitHub 操作指南

### 首次设置

```bash
# 1. GitHub 认证
gh auth login

# 2. 创建仓库
gh repo create hermes-dashboard --public --source=. --push

# 3. 初始化 git（如果还没有）
git init
git add README.md
git commit -m "docs: initial project documentation"
git branch -M main
gh repo create hermes-dashboard --public --source=. --push
```

### 每步骤的 Git 操作

```bash
# 1. 创建特性分支
git checkout -b feature/backend-sse

# 2. 实现功能...

# 3. 提交代码
git add -A
git commit -m "feat: implement backend SSE bridge"

# 4. 推送分支
git push -u origin feature/backend-sse

# 5. 创建 PR
gh pr create --title "feat: backend SSE bridge" --body "## 实现内容
- FastAPI SSE 端点
- SSE 连接管理
- 模拟 Hermès 事件源

## 测试验证
- [ ] pytest tests/backend/test_sse.py -v
- [ ] curl -N http://localhost:8000/sse

## 相关 issue
Closes #1"

# 6. QA 审核后，Lead 合并
gh pr merge <PR_NUMBER> --squash --delete-branch
```

### PR 审核流程

```bash
# QA 执行测试并评论
gh pr comment <PR_NUMBER> --body "## 测试结果
✅ pytest tests/backend/test_sse.py -v: PASS
✅ curl SSE 端点: 正常返回事件流

**QA 审核通过**"

# Lead 审核并合并
gh pr review <PR_NUMBER> --approve
gh pr merge <PR_NUMBER> --squash --delete-branch
```

## 文件变更清单

### Phase 1.1 - 后端桥接服务

| 文件 | 操作 |
|------|------|
| `backend/main.py` | 新建 |
| `backend/sse_manager.py` | 新建 |
| `backend/requirements.txt` | 新建 |
| `tests/backend/test_sse.py` | 新建 |

### Phase 1.2 - 前端骨架

| 文件 | 操作 |
|------|------|
| `frontend/src/App.vue` | 新建 |
| `frontend/src/main.ts` | 新建 |
| `frontend/src/components/TaskPanel.vue` | 新建 |
| `frontend/src/components/LogStream.vue` | 新建 |
| `frontend/src/components/HistoryList.vue` | 新建 |
| `frontend/index.html` | 新建 |
| `frontend/package.json` | 新建 |
| `frontend/vite.config.ts` | 新建 |
| `frontend/tsconfig.json` | 新建 |
| `frontend/tailwind.config.js` | 新建 |
| `tests/frontend/test_task_panel.spec.ts` | 新建 |
| `tests/frontend/test_log_stream.spec.ts` | 新建 |
| `tests/frontend/test_history_list.spec.ts` | 新建 |

## 风险与权衡

| 风险 | 应对 |
|------|------|
| Hermès 事件接口不明确 | 先用模拟数据开发，后期适配真实接口 |
| 实时数据量大导致前端卡顿 | 添加日志条数上限，虚拟滚动 |
| SSE 在某些网络环境下断开 | 添加心跳重连机制 |

## 开放问题

1. Hermès 的事件/日志以什么形式暴露？
2. 是否需要用户认证？
3. 是否需要持久化存储历史任务？
4. 是否需要支持多用户同时在线？

---

*计划生成时间：2026-04-25 20:07*
