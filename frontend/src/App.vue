<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <Sidebar :isConnected="isConnected" @nav-change="handleNavChange" />

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <TopBar
        :title="navTitleMap[currentNav] || '概览'"
        :hermesStatus="hermesStatus"
        :loading="isRefreshing"
        @refresh="handleTopRefresh"
      />

      <!-- 页面内容 -->
      <main class="main-content" :class="{ 'chat-active': currentNav === 'chat' }">
        <!-- Dashboard 概览页面 -->
        <template v-if="currentNav === 'dashboard'">
          <!-- 系统状态栏 -->
          <div class="status-bar">
            <div class="status-item">
              <span class="status-dot" :class="hermesStatus?.gateway_running ? 'success' : 'error'"></span>
              <span>Gateway {{ hermesStatus?.gateway_running ? '运行中' : '已停止' }}</span>
            </div>
            <div class="status-item">
              <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
              <span>实时推送 {{ isConnected ? '已连接' : '未连接' }}</span>
            </div>
            <div class="status-item version">
              <span>v{{ hermesStatus?.version || 'N/A' }}</span>
            </div>
          </div>

          <AgentOpsOverview
            :status="hermesStatus"
            :is-connected="isConnected"
            :tasks="tasks"
            :logs="logs"
            :history="history"
            :snapshot="overviewSnapshot"
            :loading="loadingOverview"
            @refresh="fetchOverviewSnapshot"
          />

          <AlertsPanel
            :alerts="alerts"
            :loading="loadingAlerts"
            @refresh="fetchAlerts"
            @action="handleAlertAction"
          />

          <!-- 快捷入口 -->
          <div class="quick-actions">
            <button class="quick-action" @click="handleNavChange('terminal')">
              <span class="action-icon">◎</span>
              <span class="action-label">终端</span>
              <span class="action-desc">打开终端</span>
            </button>
            <button class="quick-action" @click="handleNavChange('chat')">
              <span class="action-icon">🤖</span>
              <span class="action-label">Agent 聊天</span>
              <span class="action-desc">与 Agent 对话</span>
            </button>
            <button class="quick-action" @click="handleNavChange('tasks')">
              <span class="action-icon">☰</span>
              <span class="action-label">任务列表</span>
              <span class="action-desc">{{ tasks.length }} 个任务</span>
            </button>
            <button class="quick-action" @click="handleNavChange('logs')">
              <span class="action-icon">◷</span>
              <span class="action-label">日志</span>
              <span class="action-desc">查看运行日志</span>
            </button>
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
        </template>

        <!-- Terminal 终端页面 -->
        <template v-else-if="currentNav === 'terminal'">
          <div class="terminal-tabs">
            <div class="terminal-tab-bar">
              <button
                v-for="(tab, idx) in terminalTabs"
                :key="tab.id"
                :class="['terminal-tab', { active: activeTerminalId === tab.id }]"
                @click="switchTerminal(tab.id)"
              >
                {{ tab.name }}
                <span class="terminal-tab-close" @click.stop="closeTerminal(idx)">×</span>
              </button>
              <button class="terminal-tab-add" @click="addTerminal">+ 新终端</button>
            </div>
            <Terminal
              v-if="activeTerminalId"
              :key="activeTerminalId"
              :session-id="terminalTabs.find(t => t.id === activeTerminalId)?.sessionId || ''"
              @connected="onTerminalConnected"
            />
          </div>
        </template>

        <!-- Tasks 任务页面 -->
        <template v-else-if="currentNav === 'tasks'">
          <TaskPanel
            :tasks="tasks"
            :loading="loadingTasks"
            @pause="handlePause"
            @cancel="handleCancel"
            @refresh="fetchTasks"
          />
        </template>

        <!-- Logs 日志页面 -->
        <template v-else-if="currentNav === 'logs'">
          <LogStream :logs="logs" :loading="loadingLogs" @refresh="fetchLogs" />
        </template>

        <!-- History 历史页面 -->
        <template v-else-if="currentNav === 'history'">
          <HistoryList
            :history="history"
            :loading="loadingHistory"
            @refresh="fetchHistory"
            @viewDetails="handleViewDetails"
            @reRunTask="handleReRunTask"
          />
        </template>

        <!-- Session 复盘详情页面 -->
        <template v-else-if="currentNav === 'session-detail'">
          <SessionDetail
            :task-id="selectedSessionId"
            :item="selectedHistoryItem"
            :detail="selectedSessionDetail"
            :logs="logs"
            :trace-run="selectedTraceRun"
            :trace-spans="selectedTraceSpans"
            :rca-report="selectedRcaReport"
            :rca-loading="loadingRca"
            :runbook-report="selectedRunbook"
            :runbook-loading="loadingRunbook"
            :loading="loadingSessionDetail"
            :error="sessionDetailError"
            @back="backToHistory"
            @refresh="refreshSessionDetail"
            @analyze-rca="analyzeSessionRca"
            @generate-runbook="generateSessionRunbook"
            @open-chat="openLinkedChat"
          />
        </template>

        <!-- Agent 多智能体协作页面 -->
        <template v-else-if="currentNav === 'agents'">
          <AgentPanel />
        </template>

        <!-- 系统配置中心页面 -->
        <template v-else-if="currentNav === 'system'">
          <SystemConfigPanel />
        </template>

        <!-- Agent 聊天页面 -->
        <template v-else-if="currentNav === 'chat'">
          <AgentChat />
        </template>
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

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { onLCP, onINP, onCLS, onFCP, onTTFB } from 'web-vitals'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import TaskPanel from './components/TaskPanel.vue'
import LogStream from './components/LogStream.vue'
import HistoryList from './components/HistoryList.vue'
import Terminal from './components/Terminal.vue'
import AgentPanel from './components/AgentPanel.vue'
import AgentChat from './components/AgentChat.vue'
import AgentOpsOverview from './components/AgentOpsOverview.vue'
import SessionDetail from './components/SessionDetail.vue'
import AlertsPanel from './components/AlertsPanel.vue'
import SystemConfigPanel from './components/SystemConfigPanel.vue'
import { API_BASE } from './config'

// Navigation state
const currentNav = ref('dashboard')
const navTitleMap: Record<string, string> = {
  dashboard: '概览',
  terminal: '终端',
  tasks: '任务',
  logs: '日志',
  history: '历史',
  'session-detail': '复盘',
  chat: '聊天',
  agents: '配置',
  system: '系统'
}

function handleNavChange(navId: string) {
  currentNav.value = navId
  const navToHash: Record<string, string> = {
    dashboard: '#/',
    terminal: '#/terminal',
    tasks: '#/tasks',
    logs: '#/logs',
    history: '#/history',
    chat: '#/chat',
    agents: '#/agents',
    system: '#/system',
  }
  if (navToHash[navId]) window.location.hash = navToHash[navId]
}

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
const overviewSnapshot = ref<OverviewSnapshot>({})
const alerts = ref<AlertItem[]>([])
const selectedHistoryItem = ref<HistoryItem | null>(null)
const selectedSessionDetail = ref<SessionDetailData | null>(null)
const selectedSessionId = ref('')
const sessionDetailError = ref<string | null>(null)
const selectedTraceRun = ref<TraceRun | null>(null)
const selectedTraceSpans = ref<TraceSpan[]>([])
const selectedRcaReport = ref<RcaReport | null>(null)
const selectedRunbook = ref<RunbookReport | null>(null)

// Loading states
const loadingTasks = ref(false)
const loadingLogs = ref(false)
const loadingHistory = ref(false)
const loadingOverview = ref(false)
const loadingAlerts = ref(false)
const loadingSessionDetail = ref(false)
const loadingRca = ref(false)
const loadingRunbook = ref(false)

// Toast notifications
interface Toast {
  id: number
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
}
const toasts = ref<Toast[]>([])
let toastId = 0

// Terminal tab management
interface TerminalTab {
  id: string
  name: string
  sessionId: string  // unique per tab, passed to Terminal via prop
}

const SESSION_KEY = 'hermes_terminal_session_id'

function createTerminalSession(): string {
  const sid = Math.random().toString(36).substring(2, 10)
  return sid
}

const terminalTabs = ref<TerminalTab[]>([{
  id: 'terminal-1',
  name: 'Terminal 1',
  sessionId: localStorage.getItem(SESSION_KEY) || createTerminalSession(),
}])
const activeTerminalId = ref<string>('terminal-1')
let terminalCounter = 1

// Persist the first tab's session so page refresh reconnects to the same PTY
if (!localStorage.getItem(SESSION_KEY)) {
  localStorage.setItem(SESSION_KEY, terminalTabs.value[0].sessionId)
}

function addTerminal() {
  terminalCounter++
  const tabId = `terminal-${terminalCounter}`
  const sessionId = createTerminalSession()
  terminalTabs.value.push({ id: tabId, name: `Terminal ${terminalCounter}`, sessionId })
  activeTerminalId.value = tabId
}

function switchTerminal(id: string) {
  activeTerminalId.value = id
}

async function closeTerminal(idx: number) {
  if (terminalTabs.value.length === 1) return // Keep at least one
  const tab = terminalTabs.value[idx]
  try {
    await fetch(`${API_BASE}/api/terminal/sessions/${encodeURIComponent(tab.sessionId)}`, {
      method: 'DELETE',
    })
  } catch (e) {
    addToast('warning', `终端会话关闭请求失败，本地标签已移除`)
  }
  terminalTabs.value.splice(idx, 1)
  if (activeTerminalId.value === tab.id) {
    activeTerminalId.value = terminalTabs.value[Math.max(0, idx - 1)].id
  }
}

function onTerminalConnected() {
  // Terminal connected successfully
}

function addToast(type: Toast['type'], message: string) {
  const id = ++toastId
  toasts.value.push({ id, type, message })
  setTimeout(() => removeToast(id), 5000)
}

function removeToast(id: number) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx >= 0) toasts.value.splice(idx, 1)
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

interface SessionMessage {
  role?: string
  content?: string
  text?: string
  message?: string
  timestamp?: string
  created_at?: string
}

interface SessionDetailData {
  task_id?: string
  name?: string
  status?: string
  messages?: SessionMessage[]
  message_count?: number
  model?: string
  started_at?: string
  completed_at?: string
  duration?: number
  input_tokens?: number
  output_tokens?: number
  end_reason?: string
}

interface TraceRun {
  run_id: string
  session_id: string
  agent_id: string
  linked_session_id?: string | null
  input_summary?: string
  status: string
  started_at: string
  completed_at?: string | null
}

interface TraceSpan {
  span_id: string
  run_id: string
  span_type: string
  title: string
  summary?: string
  agent_name?: string | null
  status: string
  started_at: string
  completed_at?: string | null
}

interface RcaEvidence {
  source: string
  title: string
  detail: string
  severity: 'high' | 'medium' | 'low'
  timestamp?: string | null
  ref?: string | null
}

interface RcaReport {
  report_id: string
  session_id: string
  run_id?: string | null
  category: string
  root_cause: string
  confidence: number
  evidence: RcaEvidence[]
  next_actions: string[]
  low_confidence: boolean
  generated_at: string
  analyzer: string
}

interface RunbookReport {
  runbook_id: string
  session_id: string
  run_id?: string | null
  rca_report_id?: string | null
  title: string
  severity: string
  summary: string
  checklist: string[]
  evidence_count: number
  markdown: string
  generated_at: string
  generator: string
}

interface OverviewSnapshot {
  health?: Record<string, any> | null
  analytics?: Record<string, any> | null
  modelInfo?: Record<string, any> | null
  config?: Record<string, any> | null
  skills?: Record<string, any> | any[] | null
  cronJobs?: Record<string, any> | any[] | null
  plugins?: Record<string, any> | any[] | null
}

interface AlertItem {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  source: string
  session_id?: string | null
  action_label: string
  action_nav: string
  created_at: string
}

// Actions
function handlePause(taskId: string) {
  addToast('info', `暂停任务: ${taskId.slice(0, 8)}`)
}

function handleCancel(taskId: string) {
  addToast('warning', `取消任务: ${taskId.slice(0, 8)}`)
}

function handleViewDetails(item: HistoryItem) {
  openSessionDetail(item.task_id, item)
}

function handleReRunTask(item: HistoryItem) {
  addToast('info', `重新运行: ${item.name}`)
}

// API calls
async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
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

async function fetchOptional<T>(url: string): Promise<T | null> {
  try {
    return await fetchJSON<T>(url)
  } catch (e) {
    return null
  }
}

async function fetchOverviewSnapshot() {
  loadingOverview.value = true
  const [
    health,
    analytics,
    modelInfo,
    config,
    skills,
    cronJobs,
    plugins,
  ] = await Promise.all([
    fetchOptional<Record<string, any>>(`${API_BASE}/health`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/analytics/usage?days=7`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/model/info`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/config`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/skills`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/cron/jobs`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/plugins`),
  ])
  overviewSnapshot.value = {
    health,
    analytics,
    modelInfo,
    config,
    skills,
    cronJobs,
    plugins,
  }
  loadingOverview.value = false
}

async function fetchAlerts() {
  loadingAlerts.value = true
  try {
    const data = await fetchJSON<{ alerts: AlertItem[] }>(`${API_BASE}/api/alerts?limit=8`)
    alerts.value = data.alerts || []
  } catch (e) {
    alerts.value = []
  } finally {
    loadingAlerts.value = false
  }
}

async function fetchSessionDetail(taskId: string) {
  if (!taskId) return
  loadingSessionDetail.value = true
  sessionDetailError.value = null
  try {
    selectedSessionDetail.value = await fetchJSON<SessionDetailData>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}`)
    await fetchLatestTrace(taskId)
    await fetchLatestRca(taskId)
    await fetchLatestRunbook(taskId)
  } catch (e) {
    selectedSessionDetail.value = null
    sessionDetailError.value = e instanceof Error ? e.message : '未知错误'
    await fetchLatestTrace(taskId)
    await fetchLatestRca(taskId)
    await fetchLatestRunbook(taskId)
  } finally {
    loadingSessionDetail.value = false
  }
}

async function fetchLatestTrace(taskId: string) {
  try {
    const data = await fetchJSON<{ run: TraceRun | null; spans: TraceSpan[] }>(
      `${API_BASE}/api/agent/traces/latest?linked_session_id=${encodeURIComponent(taskId)}`
    )
    selectedTraceRun.value = data.run
    selectedTraceSpans.value = data.spans || []
  } catch (e) {
    selectedTraceRun.value = null
    selectedTraceSpans.value = []
  }
}

async function fetchLatestRca(taskId: string) {
  try {
    const data = await fetchJSON<{ report: RcaReport | null }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(taskId)}/rca`
    )
    selectedRcaReport.value = data.report
  } catch (e) {
    selectedRcaReport.value = null
  }
}

async function fetchLatestRunbook(taskId: string) {
  try {
    const data = await fetchJSON<{ runbook: RunbookReport | null }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(taskId)}/runbook`
    )
    selectedRunbook.value = data.runbook
  } catch (e) {
    selectedRunbook.value = null
  }
}

async function analyzeSessionRca() {
  if (!selectedSessionId.value || loadingRca.value) return
  loadingRca.value = true
  try {
    const data = await fetchJSON<{ report: RcaReport }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(selectedSessionId.value)}/rca`,
      { method: 'POST' }
    )
    selectedRcaReport.value = data.report
    await fetchLatestTrace(selectedSessionId.value)
    addToast('success', '失败原因分析已生成')
  } catch (e) {
    addToast('error', '失败原因分析失败')
  } finally {
    loadingRca.value = false
  }
}

async function generateSessionRunbook() {
  if (!selectedSessionId.value || loadingRunbook.value) return
  loadingRunbook.value = true
  try {
    const data = await fetchJSON<{ runbook: RunbookReport }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(selectedSessionId.value)}/runbook`,
      { method: 'POST' }
    )
    selectedRunbook.value = data.runbook
    await fetchLatestRca(selectedSessionId.value)
    await fetchLatestTrace(selectedSessionId.value)
    addToast('success', 'Runbook 已生成')
  } catch (e) {
    addToast('error', 'Runbook 生成失败')
  } finally {
    loadingRunbook.value = false
  }
}

function openSessionDetail(taskId: string, item?: HistoryItem) {
  selectedSessionId.value = taskId
  selectedHistoryItem.value = item || history.value.find(h => h.task_id === taskId) || null
  selectedSessionDetail.value = null
  selectedTraceRun.value = null
  selectedTraceSpans.value = []
  selectedRcaReport.value = null
  selectedRunbook.value = null
  currentNav.value = 'session-detail'
  window.location.hash = `#/sessions/${encodeURIComponent(taskId)}`
  void fetchSessionDetail(taskId)
}

function refreshSessionDetail() {
  if (selectedSessionId.value) void fetchSessionDetail(selectedSessionId.value)
}

function openLinkedChat() {
  if (!selectedSessionId.value) return
  currentNav.value = 'chat'
  const params = new URLSearchParams({
    linked_session_id: selectedSessionId.value,
    title: selectedSessionDetail.value?.name || selectedHistoryItem.value?.name || `Session ${selectedSessionId.value.slice(0, 8)}`,
  })
  window.location.hash = `#/chat?${params.toString()}`
}

function backToHistory() {
  selectedSessionId.value = ''
  selectedHistoryItem.value = null
  selectedSessionDetail.value = null
  selectedTraceRun.value = null
  selectedTraceSpans.value = []
  selectedRcaReport.value = null
  selectedRunbook.value = null
  sessionDetailError.value = null
  handleNavChange('history')
}

function handleAlertAction(alert: AlertItem) {
  if (alert.action_nav.startsWith('sessions/')) {
    const taskId = alert.action_nav.replace('sessions/', '')
    openSessionDetail(taskId)
    return
  }
  if (alert.action_nav === 'dashboard') {
    void fetchAlerts()
    return
  }
  handleNavChange(alert.action_nav)
}

async function handleTopRefresh() {
  if (currentNav.value === 'session-detail') {
    refreshSessionDetail()
    await fetchLogs()
    return
  }
  await refreshAll()
}

async function refreshAll() {
  isRefreshing.value = true
  await Promise.all([fetchHermesStatus(), fetchTasks(), fetchLogs(), fetchHistory(), fetchOverviewSnapshot(), fetchAlerts()])
  isRefreshing.value = false
  addToast('success', '数据已刷新')
}

// retryInit removed - unused

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
    if (typeof event.data !== 'string') return
    if (!event.data || event.data === 'undefined') return
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
  await refreshAll()
  statusPollInterval = window.setInterval(fetchHermesStatus, 30000)
  connectSSE()

  // Sync hash route to currentNav so browser back/forward and direct URL work
  const hashToNav: Record<string, string> = {
    '#/terminal': 'terminal',
    '#/tasks': 'tasks',
    '#/logs': 'logs',
    '#/history': 'history',
    '#/chat': 'chat',
    '#/agents': 'agents',
    '#/system': 'system',
    '#/': 'dashboard',
    '': 'dashboard',
  }
  const handleHashChange = () => {
    const sessionMatch = window.location.hash.match(/^#\/sessions\/(.+)$/)
    if (sessionMatch) {
      const taskId = decodeURIComponent(sessionMatch[1])
      if (selectedSessionId.value !== taskId || currentNav.value !== 'session-detail') {
        openSessionDetail(taskId)
      }
      return
    }
    const baseHash = window.location.hash.split('?')[0]
    const nav = hashToNav[baseHash]
    if (nav && currentNav.value !== nav) currentNav.value = nav
  }
  window.addEventListener('hashchange', handleHashChange)
  handleHashChange() // init from current hash

  // Core Web Vitals monitoring
  const reportWebVital = ({ name, value, id }: { name: string; value: number; id: string }) => {
    const threshold = name === 'CLS' ? 0.1 : name === 'INP' ? 200 : name === 'LCP' ? 2500 : 0
    const rating = threshold > 0 && value > threshold ? 'poor' : 'good'
    console.log(`[WebVitals] ${name}: ${value} (${rating}) [id=${id}]`)
  }
  onLCP(reportWebVital)
  onINP(reportWebVital)
  onCLS(reportWebVital)
  onFCP(reportWebVital)
  onTTFB(reportWebVital)
})

onUnmounted(() => {
  if (statusPollInterval) clearInterval(statusPollInterval)
  eventSource?.close()
})
</script>

<style>
@import './styles/minimal.css';

.app-layout {
  display: flex;
  min-height: 100vh;
  background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
}

.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

/* When chat is active, remove padding/gap so agent-chat fills the space */
.main-content.chat-active {
  padding: 0;
  gap: 0;
}

/* 系统状态栏 */
.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 24px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-item.version {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 12px;
}

/* 快捷入口 */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  box-shadow: var(--glass-shadow);
}

.quick-action:hover {
  border-color: var(--accent-color);
  box-shadow: var(--shadow-glow), var(--glass-shadow);
  transform: translateY(-2px);
}

.action-icon {
  font-size: 22px;
  line-height: 1;
  margin-bottom: 4px;
}

.action-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.action-desc {
  font-size: 12px;
  color: var(--text-muted);
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

/* Terminal tabs */
.terminal-tabs {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid #3c3c3c;
}

.terminal-tab-bar {
  display: flex;
  gap: 2px;
  padding: 8px 8px 0;
  background: #252525;
  border-bottom: none;
  flex-shrink: 0;
}

.terminal-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #2d2d2d;
  border: 1px solid #3c3c3c;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  font-size: 12px;
  color: #888888;
  cursor: pointer;
  transition: all 0.15s ease;
}

.terminal-tab.active {
  background: #1e1e1e;
  color: #cccccc;
  border-color: #3c3c3c;
}

.terminal-tab-close {
  margin-left: 4px;
  padding: 0 4px;
  font-size: 14px;
  color: #666666;
  border-radius: 2px;
}

.terminal-tab-close:hover {
  background: #ff5555;
  color: white;
}

.terminal-tab-add {
  padding: 6px 12px;
  background: transparent;
  border: 1px dashed #3c3c3c;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  font-size: 12px;
  color: #666666;
  cursor: pointer;
  transition: all 0.15s ease;
}

.terminal-tab-add:hover {
  background: #2d2d2d;
  color: #50fa7b;
  border-color: #50fa7b;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
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
  font-size: 18px;
  padding: 0;
  transition: color 0.2s ease;
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
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .main-wrapper {
    margin-left: 0;
  }
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  .panels-grid {
    grid-template-columns: 1fr;
  }
}
</style>
