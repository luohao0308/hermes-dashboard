<template>
  <div class="app-container">
    <header class="app-header">
      <h1>Hermès 工作状态监控</h1>
      <div class="header-stats">
        <span v-if="hermesStatus" class="stat-item">
          <span class="stat-label">Gateway:</span>
          <span :class="['stat-value', hermesStatus.gateway_running ? 'running' : 'stopped']">
            {{ hermesStatus.gateway_running ? '运行中' : '已停止' }}
          </span>
        </span>
        <span v-if="hermesStatus" class="stat-item">
          <span class="stat-label">活跃会话:</span>
          <span class="stat-value">{{ hermesStatus.active_sessions }}</span>
        </span>
        <span v-if="hermesStatus" class="stat-item">
          <span class="stat-label">版本:</span>
          <span class="stat-value">{{ hermesStatus.version }}</span>
        </span>
      </div>
      <div class="connection-status" :class="{ connected: isConnected }">
        <span class="status-dot"></span>
        {{ isConnected ? '已连接' : '未连接' }}
      </div>
    </header>
    <main class="app-main">
      <TaskPanel
        :tasks="tasks"
        :loading="loadingTasks"
        @pause="handlePause"
        @cancel="handleCancel"
        @refresh="fetchTasks"
      />
      <LogStream :logs="logs" :loading="loadingLogs" @refresh="fetchLogs" />
      <HistoryList :history="history" :loading="loadingHistory" @refresh="fetchHistory" />
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
  message_count?: number
  model?: string
  input_tokens?: number
  output_tokens?: number
}

// Actions
function handlePause(taskId: string) {
  console.log('Pause task:', taskId)
}

function handleCancel(taskId: string) {
  console.log('Cancel task:', taskId)
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
  } catch (e) {
    console.warn('Failed to fetch Hermes status:', e)
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
    console.error('Failed to fetch tasks:', e)
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: `获取任务列表失败: ${e}`,
      type: 'error'
    })
  } finally {
    loadingTasks.value = false
  }
}

async function fetchLogs() {
  loadingLogs.value = true
  try {
    const data = await fetchJSON<{ lines: string[] }>(`${API_BASE}/api/logs?lines=50&level=INFO`)
    logs.value = data.lines.map(line => parseLogLine(line)).filter(Boolean) as Log[]
  } catch (e) {
    console.error('Failed to fetch logs:', e)
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: `获取日志失败: ${e}`,
      type: 'error'
    })
  } finally {
    loadingLogs.value = false
  }
}

async function fetchHistory() {
  loadingHistory.value = true
  try {
    const data = await fetchJSON<{ history: any[]; total: number }>(`${API_BASE}/history?limit=20`)
    history.value = data.history.map(h => ({
      task_id: h.task_id,
      name: h.name,
      completed_at: h.completed_at,
      duration: h.duration,
      message_count: h.message_count,
      model: h.model,
      input_tokens: h.input_tokens,
      output_tokens: h.output_tokens
    }))
  } catch (e) {
    console.error('Failed to fetch history:', e)
    history.value = []
  } finally {
    loadingHistory.value = false
  }
}

function parseLogLine(line: string): Log | null {
  if (!line || typeof line !== 'string') return null
  // Try to parse log level from common formats
  const lower = line.toLowerCase()
  let type: 'info' | 'warning' | 'error' | 'debug' = 'info'
  if (lower.includes('error') || lower.includes('err]')) type = 'error'
  else if (lower.includes('warn') || lower.includes('[w]')) type = 'warning'
  else if (lower.includes('debug') || lower.includes('[d]')) type = 'debug'

  // Extract timestamp if present
  const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})/)
  const timestamp = timestampMatch ? timestampMatch[1] : new Date().toISOString()

  return {
    timestamp,
    message: line,
    type
  }
}

function handleSSEMessage(event: MessageEvent) {
  try {
    const data = JSON.parse(event.data)
    const eventType = event.type

    switch (eventType) {
      case 'connected':
        isConnected.value = true
        logs.value.unshift({
          timestamp: new Date().toISOString(),
          message: '已连接到 Hermès Bridge Service',
          type: 'info'
        })
        break

      case 'system_status':
        hermesStatus.value = {
          ...hermesStatus.value,
          status: data.status,
          gateway_running: data.gateway_running,
          active_sessions: data.active_sessions,
          version: data.version
        }
        logs.value.unshift({
          timestamp: data.timestamp || new Date().toISOString(),
          message: `系统状态更新: Gateway ${data.gateway_running ? '运行中' : '已停止'}, 活跃会话: ${data.active_sessions}`,
          type: data.status === 'healthy' ? 'info' : 'warning'
        })
        break

      case 'sessions_update':
        // Update tasks from sessions
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
        // Handle task update events
        const idx = tasks.value.findIndex(t => t.task_id === data.id || t.task_id === data.task_id)
        if (idx >= 0) {
          tasks.value[idx] = { ...tasks.value[idx], ...data }
        }
        break

      case 'heartbeat':
        // Just keep connection alive
        break

      case 'error':
        logs.value.unshift({
          timestamp: data.timestamp || new Date().toISOString(),
          message: `错误: ${data.message}`,
          type: 'error'
        })
        break

      default:
        // Unknown event type
        console.log('Unknown SSE event type:', eventType, data)
    }
  } catch (e) {
    console.error('Failed to parse SSE message:', e)
  }
}

onMounted(async () => {
  // Initial data fetch
  await Promise.all([
    fetchHermesStatus(),
    fetchTasks(),
    fetchLogs(),
    fetchHistory()
  ])

  // Poll status every 30 seconds
  statusPollInterval = window.setInterval(fetchHermesStatus, 30000)

  // Connect to SSE
  eventSource = new EventSource(`${API_BASE}/sse`)

  eventSource.addEventListener('connected', handleSSEMessage)
  eventSource.addEventListener('system_status', handleSSEMessage)
  eventSource.addEventListener('sessions_update', handleSSEMessage)
  eventSource.addEventListener('task_update', handleSSEMessage)
  eventSource.addEventListener('heartbeat', handleSSEMessage)
  eventSource.addEventListener('error', handleSSEMessage)

  eventSource.onerror = () => {
    isConnected.value = false
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: 'SSE 连接断开，正在重连...',
      type: 'warning'
    })
  }
})

onUnmounted(() => {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
  }
  eventSource?.close()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #0f172a;
  color: #e2e8f0;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  flex-wrap: wrap;
  gap: 1rem;
}

.app-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f8fafc;
}

.header-stats {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.stat-label {
  color: #94a3b8;
}

.stat-value {
  color: #e2e8f0;
  font-weight: 500;
}

.stat-value.running {
  color: #4ade80;
}

.stat-value.stopped {
  color: #f87171;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #94a3b8;
}

.connection-status.connected {
  color: #4ade80;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.connection-status.connected .status-dot {
  background: #4ade80;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.app-main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
}
</style>
