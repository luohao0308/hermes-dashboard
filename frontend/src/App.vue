<template>
  <div class="app-container">
    <!-- Toast Notifications -->
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
      >
        <span class="toast-icon">{{ toastIcon(toast.type) }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="removeToast(toast.id)">×</button>
      </div>
    </TransitionGroup>

    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <h1>Hermès 监控</h1>
        <span class="header-time">{{ currentTime }}</span>
      </div>
      <div class="header-stats">
        <template v-if="hermesStatus">
          <div class="stat-pill" :class="{ active: hermesStatus.gateway_running }">
            <span class="pill-dot"></span>
            <span class="pill-label">Gateway</span>
            <span class="pill-value">{{ hermesStatus.gateway_running ? '运行中' : '已停止' }}</span>
          </div>
          <div class="stat-pill">
            <span class="pill-label">会话</span>
            <span class="pill-value">{{ hermesStatus.active_sessions || 0 }}</span>
          </div>
          <div class="stat-pill">
            <span class="pill-label">版本</span>
            <span class="pill-value">{{ hermesStatus.version || 'N/A' }}</span>
          </div>
        </template>
        <template v-else-if="!initError">
          <div class="stat-pill loading">
            <span class="pill-spinner"></span>
            <span class="pill-label">连接中...</span>
          </div>
        </template>
      </div>
      <div class="header-right">
        <div class="connection-badge" :class="{ connected: isConnected }">
          <span class="badge-dot"></span>
          <span>{{ isConnected ? '实时同步' : '已断开' }}</span>
        </div>
        <button class="header-btn" @click="refreshAll" title="刷新全部数据">
          <span :class="{ spinning: isRefreshing }">⟳</span>
        </button>
      </div>
    </header>

    <!-- Init Error Banner -->
    <div v-if="initError" class="error-banner">
      <span class="banner-icon">⚠️</span>
      <span class="banner-text">{{ initError }}</span>
      <button class="banner-btn" @click="retryInit">重试</button>
    </div>

    <!-- Main Content -->
    <main class="app-main">
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
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import TaskPanel from './components/TaskPanel.vue'
import LogStream from './components/LogStream.vue'
import HistoryList from './components/HistoryList.vue'

const API_BASE = 'http://localhost:8000'

// Connection state
const isConnected = ref(false)
const isReconnecting = ref(false)
const isRefreshing = ref(false)
const initError = ref<string | null>(null)
const reconnectAttempts = ref(0)

// Hermes status
const hermesStatus = ref<Record<string, any> | null>(null)

// Data state
const tasks = ref<Task[]>([])
const logs = ref<Log[]>([])
const history = ref<HistoryItem[]>([])

// Loading states
const loadingTasks = ref(false)
const loadingLogs = ref(false)
const loadingHistory = ref(false)

// Toast notifications
interface Toast {
  id: number
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
}
const toasts = ref<Toast[]>([])
let toastId = 0

function addToast(type: Toast['type'], message: string) {
  const id = ++toastId
  toasts.value.push({ id, type, message })
  setTimeout(() => removeToast(id), 5000)
}

function removeToast(id: number) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx >= 0) toasts.value.splice(idx, 1)
}

function toastIcon(type: Toast['type']): string {
  return { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' }[type]
}

// Current time
const currentTime = ref('')
let timeInterval: number | null = null

function updateTime() {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Polling interval
let statusPollInterval: number | null = null
let eventSource: EventSource | null = null

// Types
interface Task {
  task_id: string
  name: string
  status: 'running' | 'pending' | 'completed'
  progress: number
  message_count?: number
  model?: string
  started_at?: string
  elapsed?: number
}

interface Log {
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error' | 'debug'
}

interface HistoryItem {
  task_id: string
  name: string
  completed_at: string
  duration: number
  status: 'success' | 'failed' | 'cancelled'
  message_count?: number
  model?: string
  input_tokens?: number
  output_tokens?: number
}

// Actions
function handlePause(taskId: string) {
  addToast('info', `暂停任务: ${taskId.slice(0, 8)}`)
}

function handleCancel(taskId: string) {
  addToast('warning', `取消任务: ${taskId.slice(0, 8)}`)
}

function handleViewDetails(item: HistoryItem) {
  addToast('info', `查看任务详情: ${item.name}`)
}

function handleReRunTask(item: HistoryItem) {
  addToast('info', `重新运行: ${item.name}`)
}

// API calls
async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
  return res.json()
}

async function fetchHermesStatus() {
  try {
    const data = await fetchJSON<any>(`${API_BASE}/api/status`)
    hermesStatus.value = data
    initError.value = null
  } catch (e) {
    if (!hermesStatus.value) {
      initError.value = `无法连接到后端服务 (${API_BASE})，请确保 Hermes Bridge Service 已启动`
    }
    hermesStatus.value = null
  }
}

async function fetchTasks() {
  loadingTasks.value = true
  try {
    const data = await fetchJSON<{ tasks: any[]; total: number }>(`${API_BASE}/tasks`)
    tasks.value = data.tasks.map(t => ({
      task_id: t.task_id,
      name: t.name,
      status: t.status,
      progress: t.progress,
      message_count: t.message_count,
      model: t.model,
      started_at: t.started_at
    }))
  } catch (e) {
    addToast('error', `获取任务列表失败`)
    tasks.value = []
  } finally {
    loadingTasks.value = false
  }
}

async function fetchLogs() {
  loadingLogs.value = true
  try {
    const data = await fetchJSON<{ logs: any[]; lines?: string[] }>(`${API_BASE}/api/logs?lines=50&level=INFO`)
    if (data.logs) {
      logs.value = data.logs.map((l: any) => ({
        timestamp: l.timestamp || new Date().toISOString(),
        message: l.message || l,
        type: l.level?.toLowerCase() || 'info'
      }))
    } else if (data.lines) {
      logs.value = data.lines.map(line => parseLogLine(line)).filter(Boolean) as Log[]
    }
  } catch (e) {
    addToast('error', `获取日志失败`)
  } finally {
    loadingLogs.value = false
  }
}

async function fetchHistory() {
  loadingHistory.value = true
  try {
    const data = await fetchJSON<{ history: any[]; total: number }>(`${API_BASE}/history?limit=20`)
    history.value = data.history.map((h: any) => ({
      task_id: h.task_id,
      name: h.name,
      completed_at: h.completed_at,
      duration: h.duration,
      status: 'success' as const,
      message_count: h.message_count,
      model: h.model,
      input_tokens: h.input_tokens,
      output_tokens: h.output_tokens
    }))
  } catch (e) {
    addToast('error', `获取历史记录失败`)
    history.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function refreshAll() {
  isRefreshing.value = true
  await Promise.all([fetchHermesStatus(), fetchTasks(), fetchLogs(), fetchHistory()])
  isRefreshing.value = false
  addToast('success', '数据已刷新')
}

async function retryInit() {
  initError.value = null
  await refreshAll()
}

function parseLogLine(line: string): Log | null {
  if (!line || typeof line !== 'string') return null
  const lower = line.toLowerCase()
  let type: 'info' | 'warning' | 'error' | 'debug' = 'info'
  if (lower.includes('error') || lower.includes('err]')) type = 'error'
  else if (lower.includes('warn') || lower.includes('[w]')) type = 'warning'
  else if (lower.includes('debug') || lower.includes('[d]')) type = 'debug'

  const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})/)
  const timestamp = timestampMatch ? timestampMatch[1] : new Date().toISOString()

  return { timestamp, message: line, type }
}

function handleSSEMessage(event: MessageEvent) {
  try {
    const data = JSON.parse(event.data)
    const eventType = event.type

    switch (eventType) {
      case 'connected':
        isConnected.value = true
        break

      case 'system_status':
        hermesStatus.value = {
          ...hermesStatus.value,
          status: data.status,
          gateway_running: data.gateway_running,
          active_sessions: data.active_sessions,
          version: data.version
        }
        break

      case 'sessions_update':
        if (data.sessions) {
          tasks.value = data.sessions.map((s: any) => ({
            task_id: s.id,
            name: s.title || `Session ${s.id?.slice(0, 8)}`,
            status: s.is_active ? 'running' : 'completed',
            progress: s.is_active ? 50 : 100,
            message_count: s.message_count,
            model: s.model,
            started_at: s.started_at ? new Date(s.started_at).toISOString() : undefined
          }))
        }
        break

      case 'task_update':
        const idx = tasks.value.findIndex(t => t.task_id === data.id || t.task_id === data.task_id)
        if (idx >= 0) {
          tasks.value[idx] = { ...tasks.value[idx], ...data }
        }
        break

      case 'heartbeat':
        break

      case 'error':
        addToast('error', data.message || 'SSE 错误')
        break

      default:
        console.log('Unknown SSE event:', eventType, data)
    }
  } catch (e) {
    console.error('Failed to parse SSE message:', e)
  }
}

// SSE reconnect config
const MAX_RECONNECT_DELAY = 30000 // 30s max
const BASE_RECONNECT_DELAY = 1000 // 1s initial
const MAX_RECONNECT_ATTEMPTS = 10

function getReconnectDelay(attempt: number): number {
  // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
  return Math.min(BASE_RECONNECT_DELAY * Math.pow(2, attempt), MAX_RECONNECT_DELAY)
}

function connectSSE() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }

  eventSource = new EventSource(`${API_BASE}/sse`)

  eventSource.addEventListener('connected', handleSSEMessage)
  eventSource.addEventListener('system_status', handleSSEMessage)
  eventSource.addEventListener('sessions_update', handleSSEMessage)
  eventSource.addEventListener('task_update', handleSSEMessage)
  eventSource.addEventListener('heartbeat', handleSSEMessage)
  eventSource.addEventListener('error', handleSSEMessage)

  eventSource.onopen = () => {
    isConnected.value = true
    isReconnecting.value = false
    reconnectAttempts.value = 0
    // Clear any reconnect error toasts
  }

  eventSource.onerror = () => {
    isConnected.value = false
    eventSource?.close()

    if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
      addToast('error', `SSE 连接失败，已停止重连。请刷新页面重试。`)
      return
    }

    const delay = getReconnectDelay(reconnectAttempts.value)
    reconnectAttempts.value++

    if (!isReconnecting.value) {
      isReconnecting.value = true
      addToast('warning', `SSE 连接断开，${Math.round(delay / 1000)}s 后自动重连...`)
    }

    setTimeout(connectSSE, delay)
  }
}

onMounted(async () => {
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)

  await refreshAll()
  statusPollInterval = window.setInterval(fetchHermesStatus, 30000)

  connectSSE()
})

onUnmounted(() => {
  if (statusPollInterval) clearInterval(statusPollInterval)
  if (timeInterval) clearInterval(timeInterval)
  eventSource?.close()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #0f172a;
  color: #e2e8f0;
}

/* Toast Notifications */
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: #1e293b;
  border-radius: 0.5rem;
  border-left: 4px solid;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  font-size: 0.875rem;
}

.toast-info { border-color: #3b82f6; }
.toast-success { border-color: #22c55e; }
.toast-warning { border-color: #f59e0b; }
.toast-error { border-color: #ef4444; }

.toast-icon { font-size: 1rem; }
.toast-message { flex: 1; }
.toast-close {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0;
  line-height: 1;
}
.toast-close:hover { color: #e2e8f0; }

.toast-enter-active { animation: slideIn 0.3s ease; }
.toast-leave-active { animation: slideOut 0.3s ease; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes slideOut {
  from { transform: translateX(0); opacity: 1; }
  to { transform: translateX(100%); opacity: 0; }
}

/* Header */
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  border-bottom: 1px solid #334155;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 1rem;
}

.app-header h1 {
  font-size: 1.375rem;
  font-weight: 700;
  background: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-time {
  font-size: 0.75rem;
  color: #64748b;
  font-family: monospace;
}

.header-stats {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: #0f172a;
  border-radius: 9999px;
  border: 1px solid #334155;
  font-size: 0.75rem;
}

.stat-pill.loading {
  border-color: #3b82f6;
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #64748b;
}

.stat-pill.active .pill-dot {
  background: #22c55e;
  box-shadow: 0 0 6px #22c55e;
}

.pill-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #334155;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.pill-label { color: #64748b; }
.pill-value { color: #e2e8f0; font-weight: 500; }

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.875rem;
  background: #0f172a;
  border-radius: 9999px;
  font-size: 0.75rem;
  color: #64748b;
  border: 1px solid #334155;
}

.connection-badge.connected {
  color: #22c55e;
  border-color: #22c55e30;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #64748b;
}

.connection-badge.connected .badge-dot {
  background: #22c55e;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 #22c55e40; }
  50% { opacity: 0.8; box-shadow: 0 0 0 4px #22c55e00; }
}

.header-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.5rem;
  color: #94a3b8;
  cursor: pointer;
  font-size: 1.125rem;
  transition: all 0.2s;
}

.header-btn:hover {
  background: #1e293b;
  color: #e2e8f0;
  border-color: #475569;
}

.header-btn .spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

/* Error Banner */
.error-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(90deg, #7f1d1d 0%, #991b1b 100%);
  color: #fecaca;
  font-size: 0.875rem;
}

.banner-icon { font-size: 1.125rem; }
.banner-text { flex: 1; }
.banner-btn {
  padding: 0.375rem 0.875rem;
  background: #dc2626;
  border: none;
  border-radius: 0.375rem;
  color: white;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}
.banner-btn:hover { background: #b91c1c; }

/* Main Content */
.app-main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
}

@media (max-width: 900px) {
  .app-main {
    grid-template-columns: 1fr;
  }
}
</style>
