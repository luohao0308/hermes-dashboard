# Hermès Dashboard UI 重构计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 将 Hermès Dashboard 前端从深色主题改造为极简中台风格 —— 纯白背景、左侧边栏、精简 Banner，像一个前端大厂工程师做的产品。

**Architecture:** 采用经典中台布局：左侧固定侧边栏 + 右侧主内容区。移除深色主题，改为以白色为底、灰色辅助色为主调的极简设计。保持现有 API 集成不变，仅重构 UI 结构和样式。

**Tech Stack:** Vue 3 + Vite + TailwindCSS + Naive UI（现有技术栈不变）

---

## 目录结构

```
frontend/src/
├── App.vue                    # 重构：侧边栏 + 主内容区布局
├── components/
│   ├── Sidebar.vue           # 新增：极简侧边栏组件
│   ├── TopBar.vue            # 新增：精简顶部栏（替代原有 Header）
│   ├── TaskPanel.vue         # 修改：适配极简风格
│   ├── LogStream.vue         # 修改：适配极简风格
│   └── HistoryList.vue       # 修改：适配极简风格
├── styles/
│   └── minimal.css           # 新增：极简风格全局样式变量
└── main.ts                   # 修改：导入极简样式
```

---

## Task 1: 创建极简风格全局样式

**Objective:** 定义极简风格所需的 CSS 变量和全局样式

**Files:**
- Create: `frontend/src/styles/minimal.css`

**Step 1: 创建极简样式文件**

```css
/* Hermès Dashboard - 极简中台风格 */

:root {
  /* 极简配色 */
  --bg-primary: #ffffff;
  --bg-secondary: #fafafa;
  --bg-tertiary: #f5f5f5;
  --border-color: #e5e5e5;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --text-muted: #999999;
  --accent-color: #0066ff;
  --accent-hover: #0052cc;
  --success-color: #10b981;
  --warning-color: #f59e0b;
  --error-color: #ef4444;

  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);

  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* 间距 */
  --sidebar-width: 240px;
  --topbar-height: 56px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 极简卡片 */
.card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.card-body {
  padding: 20px;
}

/* 极简按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--accent-color);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--border-color);
}

/* 极简输入框 */
.input {
  padding: 8px 12px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s ease;
}

.input:focus {
  border-color: var(--accent-color);
}

/* 状态指示器 */
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.success { background: var(--success-color); }
.status-dot.warning { background: var(--warning-color); }
.status-dot.error { background: var(--error-color); }
.status-dot.idle { background: var(--text-muted); }

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
```

**Step 2: 提交**

```bash
git add frontend/src/styles/minimal.css
git commit -m "feat: add minimalist global styles"
```

---

## Task 2: 创建 Sidebar 组件

**Objective:** 实现左侧极简侧边栏，包含 Logo、导航菜单

**Files:**
- Create: `frontend/src/components/Sidebar.vue`

**Step 1: 创建侧边栏组件**

```vue
<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">H</div>
      <span class="logo-text">Hermès</span>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.id"
        :class="['nav-item', { active: activeNav === item.id }]"
        @click="activeNav = item.id"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </a>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <div class="connection-status">
        <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
        <span class="status-text">{{ isConnected ? '已连接' : '未连接' }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface NavItem {
  id: string
  label: string
  icon: string
}

const props = defineProps<{
  isConnected?: boolean
}>()

const navItems: NavItem[] = [
  { id: 'dashboard', label: '概览', icon: '◈' },
  { id: 'tasks', label: '任务', icon: '◎' },
  { id: 'logs', label: '日志', icon: '☰' },
  { id: 'history', label: '历史', icon: '◷' },
]

const activeNav = ref('dashboard')
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-logo {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 28px;
  height: 28px;
  background: var(--text-primary);
  color: white;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.logo-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
}

.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: 500;
}

.nav-icon {
  font-size: 16px;
  opacity: 0.7;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-text {
  color: var(--text-secondary);
}
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/Sidebar.vue
git commit -m "feat: add minimalist sidebar component"
```

---

## Task 3: 创建 TopBar 组件

**Objective:** 实现精简顶部栏，显示页面标题和关键状态

**Files:**
- Create: `frontend/src/components/TopBar.vue`

**Step 1: 创建顶部栏组件**

```vue
<template>
  <header class="topbar">
    <div class="topbar-left">
      <h1 class="page-title">{{ title }}</h1>
    </div>
    <div class="topbar-right">
      <!-- Hermès 状态 -->
      <div v-if="hermesStatus" class="status-badges">
        <div class="badge">
          <span class="status-dot" :class="hermesStatus.gateway_running ? 'success' : 'error'"></span>
          <span>Gateway {{ hermesStatus.gateway_running ? '运行中' : '已停止' }}</span>
        </div>
        <div class="badge">
          <span>{{ hermesStatus.active_sessions || 0 }} 个会话</span>
        </div>
        <div class="badge">
          <span>v{{ hermesStatus.version || 'N/A' }}</span>
        </div>
      </div>
      <!-- 刷新按钮 -->
      <button class="btn btn-secondary" @click="$emit('refresh')" :disabled="loading">
        <span :class="{ spinning: loading }">⟳</span>
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  hermesStatus?: Record<string, any> | null
  loading?: boolean
}>()

defineEmits<{
  refresh: []
}>()
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.topbar-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.btn.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/TopBar.vue
git commit -m "feat: add minimalist topbar component"
```

---

## Task 4: 重构 App.vue 布局

**Objective:** 将 App.vue 改为侧边栏 + 主内容区布局，移除原有的深色 Header，保留数据逻辑

**Files:**
- Modify: `frontend/src/App.vue`

**Step 1: 重写 App.vue 模板部分**

将 `<template>` 部分替换为：

```vue
<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <Sidebar :isConnected="isConnected" />

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <TopBar
        title="概览"
        :hermesStatus="hermesStatus"
        :loading="isRefreshing"
        @refresh="refreshAll"
      />

      <!-- 页面内容 -->
      <main class="main-content">
        <!-- 概览卡片 -->
        <div class="overview-grid">
          <div class="overview-card">
            <div class="overview-label">活跃会话</div>
            <div class="overview-value">{{ hermesStatus?.active_sessions || 0 }}</div>
          </div>
          <div class="overview-card">
            <div class="overview-label">Gateway 状态</div>
            <div class="overview-value">
              <span class="status-dot" :class="hermesStatus?.gateway_running ? 'success' : 'error'"></span>
              {{ hermesStatus?.gateway_running ? '运行中' : '已停止' }}
            </div>
          </div>
          <div class="overview-card">
            <div class="overview-label">版本</div>
            <div class="overview-value">{{ hermesStatus?.version || 'N/A' }}</div>
          </div>
          <div class="overview-card">
            <div class="overview-label">连接状态</div>
            <div class="overview-value">
              <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
              {{ isConnected ? '已连接' : '未连接' }}
            </div>
          </div>
        </div>

        <!-- 功能面板 -->
        <div class="panels-grid">
          <TaskPanel
            :tasks="tasks"
            :loading="loadingTasks"
            @pause="handlePause"
            @cancel="handleCancel"
            @refresh="fetchTasks"
          />
          <LogStream :logs="logs" :loading="loadingLogs" @refresh="fetchLogs" />
          <HistoryList
            :history="history"
            :loading="loadingHistory"
            @refresh="fetchHistory"
            @viewDetails="handleViewDetails"
            @reRunTask="handleReRunTask"
          />
        </div>
      </main>
    </div>

    <!-- Toast 通知 -->
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div v-for="toast in toasts" :key="toast.id" :class="['toast', `toast-${toast.type}`]">
        <span>{{ toast.message }}</span>
        <button class="toast-close" @click="removeToast(toast.id)">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>
```

**Step 2: 替换样式部分**

将 `<style>` 部分替换为：

```vue
<style>
@import './styles/minimal.css';

.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-secondary);
}

.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 概览网格 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.overview-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.overview-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.overview-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 功能面板网格 */
.panels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

/* Toast */
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  font-size: 13px;
  color: var(--text-primary);
  min-width: 280px;
}

.toast-success { border-left: 3px solid var(--success-color); }
.toast-error { border-left: 3px solid var(--error-color); }
.toast-warning { border-left: 3px solid var(--warning-color); }
.toast-info { border-left: 3px solid var(--accent-color); }

.toast-close {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 16px;
  padding: 0;
}

.toast-close:hover {
  color: var(--text-primary);
}

.toast-enter-active { animation: slideIn 0.2s ease; }
.toast-leave-active { animation: slideOut 0.2s ease; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOut {
  from { transform: translateX(0); opacity: 1; }
  to { transform: translateX(100%); opacity: 0; }
}

@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .main-wrapper {
    margin-left: 0;
  }
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .panels-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

**Step 3: 提交**

```bash
git add frontend/src/App.vue
git commit -m "refactor: restructure App.vue with sidebar layout"
```

---

## Task 5: 修改 TaskPanel.vue 适配极简风格

**Objective:** 将 TaskPanel 卡片样式改为极简白色卡片

**Files:**
- Modify: `frontend/src/components/TaskPanel.vue` (仅样式部分)

**Step 1: 替换样式部分**

将 TaskPanel 的 `<style scoped>` 部分替换为极简样式。关键变更：
- 卡片背景从深色改为白色 + 边框
- 文字颜色从浅色改为深色
- 进度条颜色调整为蓝灰色调

```vue
<style scoped>
.task-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-body {
  padding: 0;
}

.task-list {
  list-style: none;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s ease;
}

.task-item:last-child {
  border-bottom: none;
}

.task-item:hover {
  background: var(--bg-secondary);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.task-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.task-status.running {
  background: #e6f0ff;
  color: var(--accent-color);
}

.task-status.completed {
  background: #f0fdf4;
  color: var(--success-color);
}

.task-status.pending {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

/* 骨架屏 */
.skeleton {
  background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary) 50%, var(--bg-secondary) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/TaskPanel.vue
git commit -m "refactor: update TaskPanel to minimalist style"
```

---

## Task 6: 修改 LogStream.vue 适配极简风格

**Objective:** 将 LogStream 卡片样式改为极简白色卡片

**Files:**
- Modify: `frontend/src/components/LogStream.vue` (仅样式部分)

**Step 1: 替换样式部分**

将 LogStream 的 `<style scoped>` 部分替换为极简样式。关键变更：
- 保持单行日志展示，字体等宽
- 日志级别颜色改为灰色系

```vue
<style scoped>
.log-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-body {
  max-height: 320px;
  overflow-y: auto;
  background: var(--bg-secondary);
}

.log-list {
  list-style: none;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 6px 20px;
  border-bottom: 1px solid var(--border-color);
  line-height: 1.6;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-message {
  color: var(--text-secondary);
  word-break: break-all;
}

.log-item.error .log-message { color: var(--error-color); }
.log-item.warning .log-message { color: var(--warning-color); }

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/LogStream.vue
git commit -m "refactor: update LogStream to minimalist style"
```

---

## Task 7: 修改 HistoryList.vue 适配极简风格

**Objective:** 将 HistoryList 卡片样式改为极简白色卡片

**Files:**
- Modify: `frontend/src/components/HistoryList.vue` (仅样式部分)

**Step 1: 替换样式部分**

将 HistoryList 的 `<style scoped>` 部分替换为极简样式。

```vue
<style scoped>
.history-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th {
  text-align: left;
  padding: 12px 20px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.history-table td {
  padding: 12px 20px;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.history-table tr:last-child td {
  border-bottom: none;
}

.history-table tr:hover td {
  background: var(--bg-secondary);
}

.history-name {
  color: var(--text-primary);
  font-weight: 500;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.status-badge.success {
  background: #f0fdf4;
  color: var(--success-color);
}

.status-badge.failed {
  background: #fef2f2;
  color: var(--error-color);
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/HistoryList.vue
git commit -m "refactor: update HistoryList to minimalist style"
```

---

## Task 8: 更新 main.ts 导入极简样式

**Objective:** 确保 main.ts 导入新的极简样式文件

**Files:**
- Modify: `frontend/src/main.ts`

**Step 1: 检查并更新 main.ts**

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import './styles/minimal.css'

createApp(App).mount('#app')
```

**Step 2: 提交**

```bash
git add frontend/src/main.ts
git commit -m "chore: import minimalist styles in main.ts"
```

---

## Task 9: 更新 README 文档

**Objective:** 更新 README.md，反映新的 UI 设计方向和架构变更

**Files:**
- Modify: `README.md`

**Step 1: 更新 README 关键章节**

在 README.md 中更新以下部分：

1. **技术方案**表格中 UI 组件行更新为：`TailwindCSS + Naive UI（极简中台风格）`

2. **目录结构**中新增：
   ```
   ├── frontend/src/
   │   ├── styles/
   │   │   └── minimal.css    # 极简风格全局样式
   │   └── components/
   │       ├── Sidebar.vue    # 左侧导航栏
   │       └── TopBar.vue     # 顶部状态栏
   ```

3. **Phase 3.3**（UI 风格重构）新增章节：
   ```
   #### Task 3.3: UI 风格重构 - 极简中台风 ✅
   - **分支**: `feature/ui-minimalist` (待创建)
   - **完成时间**: 2026-04-26
   - **实现内容**:
     - 极简中台风格：纯白背景、左侧边栏、精简 Banner
     - 全局样式变量系统 (minimal.css)
     - 侧边栏组件 (Sidebar.vue)
     - 顶部状态栏 (TopBar.vue)
     - 各面板组件适配极简风格
   ```

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README with UI redesign info"
```

---

## 验证步骤

所有任务完成后，执行以下验证：

```bash
# 1. 启动服务
cd ~/Desktop/hermes_workspace/hermes_free
./start.sh

# 2. 检查前端编译
# 访问 http://localhost:5173
# 预期：纯白背景、左侧深色侧边栏、顶部精简 Banner

# 3. 运行测试
cd frontend && npm run test

# 4. TypeScript 类型检查
npx vue-tsc --noEmit
```

---

## 风险与权衡

| 风险 | 应对 |
|------|------|
| 极简风格与现有 Naive UI 组件可能冲突 | 仅使用 TailwindCSS 基础样式，避免 Naive UI 深色主题 |
| 响应式布局在移动端可能不友好 | 已添加 media query 处理小屏幕 |
| 移除深色主题后对比度变化 | 确保文字颜色符合 WCAG 可读性标准 |

---

## 开放问题

1. ~~Hermès 事件接口不明确~~ → 已解决
2. ~~前端 vitest 测试~~ → 已实现
3. ~~E2E 测试 (Playwright)~~ → 已实现
4. ~~SSE 断连自动重连~~ → 已实现
5. ~~生产环境 Docker 部署~~ → 已实现
6. **UI 极简风格重构** → 本次计划
