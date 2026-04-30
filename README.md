# AI Code Review Pipeline

基于多模型共识的代码审查平台。多个 LLM 模型并行审查同一个 PR，只有被多个模型一致同意的问题才会展示，减少误报。

## 功能特性

- **多模型共识审查** — 2-3 个模型并行审查，共识过滤误报
- **多 Provider 支持** — OpenAI、Anthropic、小米 MiMo、MiniMax、Ollama
- **自定义模型** — 任意 OpenAI 兼容 API 均可接入
- **GitHub PR 集成** — 自动拉取 PR 列表，一键触发审查
- **成本追踪** — 按模型/周期统计 token 用量和费用
- **审查规则** — 可配置严重程度过滤器（阻止/警告/跳过）
- **中文界面** — 全中文 UI

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 20+

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/luohao0308/hermes-dashboard.git
cd hermes-dashboard

# 2. 配置环境变量
cat > .env << 'EOF'
GITHUB_TOKEN=ghp_你的GitHub Token
OPENAI_API_KEY=sk_你的OpenAI密钥
XIAOMI_API_KEY=你的小米MiMo密钥
EOF

# 3. 启动
./start.sh
```

访问 http://localhost:5173

### 停止

```bash
./stop.sh
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `GITHUB_TOKEN` | 是 | GitHub Personal Access Token（需要 repo 权限） |
| `OPENAI_API_KEY` | 否 | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | 否 | Anthropic API 密钥 |
| `XIAOMI_API_KEY` | 否 | 小米 MiMo API 密钥 |
| `MINIMAX_API_KEY` | 否 | MiniMax API 密钥 |

至少配置一个 LLM API Key 才能执行审查。

## 使用方式

### 代码审查

1. 打开「代码审查」页面
2. 输入仓库地址（如 `owner/repo`）
3. 点击「刷新」加载 PR 列表
4. 点击「开始审查」触发多模型审查
5. 查看审查结果弹窗

### 模型管理

- 「模型管理」页面查看所有已配置的 Provider
- 下拉框切换默认模型
- 点击「编辑配置」修改 API 地址、密钥
- 点击「+ 添加自定义模型」接入任意 OpenAI 兼容 API

### 成本查看

- 「成本」页面查看 token 用量和费用统计
- 支持按日/周/月切换时间范围

## 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Vue 3 前端  │────▶│ FastAPI 后端  │────▶│  GitHub API │
│  (Vite)     │◀────│  (SSE 推送)   │     └─────────────┘
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  LLM Providers│
                    ├──────────────┤
                    │ OpenAI       │
                    │ Anthropic    │
                    │ 小米 MiMo    │
                    │ MiniMax      │
                    │ Ollama       │
                    │ 自定义...    │
                    └──────────────┘
```

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Python FastAPI + SSE |
| 存储 | SQLite（成本追踪） + YAML（配置） |
| 实时通信 | Server-Sent Events |

## 目录结构

```
hermes_free/
├── .env                    # 环境变量（不提交）
├── start.sh                # 启动脚本
├── stop.sh                 # 停止脚本
├── backend/
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 配置
│   ├── cost_tracker.py     # 成本追踪
│   ├── provider/           # LLM Provider 抽象层
│   │   ├── interface.py    # LLMProvider ABC
│   │   ├── registry.py     # Provider 注册表
│   │   ├── providers.yaml  # Provider 配置
│   │   └── adapters/       # 各 Provider 适配器
│   ├── review/             # 代码审查流水线
│   │   ├── pipeline.py     # 审查编排
│   │   ├── consensus.py    # 共识引擎
│   │   ├── github_adapter.py
│   │   └── review_store.py
│   └── tests/
└── frontend/
    ├── src/
    │   ├── App.vue
    │   └── components/
    │       ├── Sidebar.vue
    │       ├── ReviewDashboard.vue
    │       ├── ProviderPanel.vue
    │       ├── CostDashboard.vue
    │       └── GuardrailsPanel.vue
    └── package.json
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/providers` | 列出所有 Provider |
| POST | `/api/providers/{name}/test` | 测试 Provider 连接 |
| PUT | `/api/providers/{name}` | 更新 Provider 配置 |
| POST | `/api/providers/custom` | 添加自定义 Provider |
| GET | `/api/github/prs` | 列出 GitHub PR |
| POST | `/api/reviews/trigger` | 触发代码审查 |
| GET | `/api/reviews` | 查看审查记录 |
| GET | `/api/reviews/stats` | 审查统计 |
| GET | `/api/cost/summary` | 成本统计 |
| GET | `/api/cost/breakdown` | 成本明细 |

## License

MIT
