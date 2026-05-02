<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <Sidebar :isConnected="isConnected" @nav-change="handleNavChange" />

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <TopBar
        :title="navTitleMap[currentNav] || 'Dashboard'"
        :hermesStatus="hermesStatus"
        :loading="isRefreshing"
        @refresh="handleTopRefresh"
      />

      <!-- 页面内容 -->
      <main class="main-content" :class="{ 'chat-active': currentNav === 'chat' }">
        <!-- Legacy Deprecation Banner -->
        <div v-if="isLegacyNav(currentNav)" class="legacy-banner">
          <span class="legacy-banner-icon">⚠</span>
          <span>{{ t('dashboard.legacyBanner') }}</span>
        </div>
        <!-- Dashboard 概览页面 -->
        <template v-if="currentNav === 'dashboard'">
          <!-- System Status Bar -->
          <div class="status-bar">
            <div class="status-item">
              <span class="status-dot" :class="hermesStatus?.gateway_running ? 'success' : 'error'"></span>
              <span>{{ hermesStatus?.gateway_running ? t('dashboard.gatewayRunning') : t('dashboard.gatewayStopped') }}</span>
            </div>
            <div class="status-item">
              <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
              <span>{{ isConnected ? t('dashboard.realtimeConnected') : t('dashboard.realtimeDisconnected') }}</span>
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
            @runbook="handleAlertRunbook"
          />

          <!-- Quick Actions -->
          <div class="quick-actions">
            <button class="quick-action" @click="handleNavChange('runs')">
              <span class="action-icon">▶</span>
              <span class="action-label">{{ t('dashboard.runs') }}</span>
              <span class="action-desc">{{ t('dashboard.runsDesc') }}</span>
            </button>
            <button class="quick-action" @click="handleNavChange('workflows')">
              <span class="action-icon">◇</span>
              <span class="action-label">{{ t('dashboard.workflows') }}</span>
              <span class="action-desc">{{ t('dashboard.workflowsDesc') }}</span>
            </button>
            <button class="quick-action" @click="handleNavChange('approvals')">
              <span class="action-icon">☑</span>
              <span class="action-label">{{ t('dashboard.approvals') }}</span>
              <span class="action-desc">{{ t('dashboard.approvalsDesc') }}</span>
            </button>
            <button class="quick-action" @click="handleNavChange('eval')">
              <span class="action-icon">📊</span>
              <span class="action-label">{{ t('dashboard.eval') }}</span>
              <span class="action-desc">{{ t('dashboard.evalDesc') }}</span>
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
              <button class="terminal-tab-add" @click="addTerminal">+ {{ t('dashboard.newTerminal') }}</button>
            </div>
            <div
              v-for="tab in terminalTabs"
              :key="tab.id"
              v-show="activeTerminalId === tab.id"
              class="terminal-pane"
            >
              <Terminal
                :session-id="tab.sessionId"
                :active="activeTerminalId === tab.id"
                @connected="onTerminalConnected"
              />
            </div>
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
            :export-loading="exportingMarkdown"
            :loading="loadingSessionDetail"
            :error="sessionDetailError"
            @back="backToHistory"
            @refresh="refreshSessionDetail"
            @analyze-rca="analyzeSessionRca"
            @generate-runbook="generateSessionRunbook"
            @confirm-runbook-step="confirmRunbookStep"
            @execute-runbook-step="executeRunbookStep"
            @export-markdown="exportSessionMarkdown"
            @open-chat="openLinkedChat"
          />
        </template>

        <!-- Agent 多智能体协作页面 -->
        <template v-else-if="currentNav === 'agents'">
          <AgentPanel />
        </template>

        <!-- 系统配置中心页面 -->
        <template v-else-if="currentNav === 'system'">
          <HealthMatrix
            :health="healthData"
            :metrics="metricsData"
            :loading="loadingHealth"
            @refresh="fetchHealth"
          />
          <SystemConfigPanel />
        </template>

        <!-- 事故知识库页面 -->
        <template v-else-if="currentNav === 'knowledge'">
          <KnowledgeSearch />
        </template>

        <!-- Agent 聊天页面 -->
        <template v-else-if="currentNav === 'chat'">
          <AgentChat />
        </template>

        <!-- Pull Requests 审查列表 -->
        <template v-else-if="currentNav === 'pr-list'">
          <ReviewDashboard />
        </template>

        <!-- Providers 多模型管理 -->
        <template v-else-if="currentNav === 'providers'">
          <ProviderPanel />
        </template>

        <!-- 成本追踪 -->
        <template v-else-if="currentNav === 'costs'">
          <CostDashboard />
        </template>

        <!-- Guardrails 审查规则 -->
        <template v-else-if="currentNav === 'guardrails'">
          <GuardrailsPanel />
        </template>

        <!-- Workflow Runs (v1.0) -->
        <template v-else-if="currentNav === 'runs'">
          <RunList
            :runs="workflowRuns"
            :runtimes="workflowRuntimes"
            :connectorTypes="connectorTypeOptions"
            :total="workflowRunsTotal"
            :limit="workflowRunsLimit"
            :offset="workflowRunsOffset"
            :loading="loadingWorkflowRuns"
            @refresh="fetchWorkflowRuns"
            @selectRun="openRunDetail"
            @filterChange="handleWorkflowFilterChange"
            @pageChange="handleWorkflowPageChange"
          />
        </template>

        <!-- Workflow Run Detail (v1.0) -->
        <template v-else-if="currentNav === 'run-detail'">
          <RunDetail
            :runId="selectedRunId"
            :run="selectedRun"
            :spans="selectedRunSpans"
            :loading="loadingRunDetail"
            :error="runDetailError"
            :rcaReport="selectedRcaReport"
            :runbook="selectedRunbook"
            :loadingRca="loadingRca"
            :loadingRunbook="loadingRunbook"
            @back="backToRuns"
            @refresh="refreshRunDetail"
            @analyzeRca="handleAnalyzeRca"
            @generateRunbook="handleGenerateRunbook"
            @exportRca="handleExportRca"
            @exportRunbook="handleExportRunbook"
          />
        </template>

        <!-- Approval Inbox (v1.1) -->
        <template v-else-if="currentNav === 'approvals'">
          <ApprovalInbox
            :approvals="approvalItems"
            :total="approvalTotal"
            :limit="approvalLimit"
            :offset="approvalOffset"
            :loading="loadingApprovals"
            :actionLoading="approvalActionLoading"
            @refresh="fetchApprovals"
            @approve="handleApprove"
            @reject="handleReject"
            @filterChange="handleApprovalFilterChange"
            @pageChange="handleApprovalPageChange"
            @batchApprove="handleBatchApprove"
            @batchReject="handleBatchReject"
          />
        </template>

        <template v-else-if="currentNav === 'eval'">
          <EvalDashboard
            :summary="evalSummary"
            :loading="loadingEval"
            @refresh="fetchEvalSummary"
          />
        </template>

        <template v-else-if="currentNav === 'config-compare'">
          <ConfigCompare
            :versions="configVersions"
            :result="configCompareResult"
            :loading="loadingConfigCompare"
            @compare="handleConfigCompare"
            @refresh="fetchConfigVersions"
          />
        </template>

        <!-- Connectors / Failed Events (OPT-54) -->
        <template v-else-if="currentNav === 'connectors'">
          <FailedEventsPanel
            :events="failedEvents"
            :connectors="connectorItems"
            :total="failedEventsTotal"
            :limit="failedEventsLimit"
            :offset="failedEventsOffset"
            :hasMore="failedEventsHasMore"
            :loading="loadingFailedEvents"
            :replayingId="replayingFailedEventId"
            @refresh="fetchFailedEvents"
            @replay="handleReplayFailedEvent"
            @connectorChange="handleFailedEventConnectorChange"
            @pageChange="handleFailedEventPageChange"
            @nextPage="handleFailedEventsNextPage"
            @prevPage="handleFailedEventsPrevPage"
          />
        </template>

        <!-- Workflow Definitions (v2.0) -->
        <template v-else-if="currentNav === 'workflows'">
          <WorkflowList
            :workflows="workflowDefinitions"
            :total="workflowDefsTotal"
            :limit="workflowDefsLimit"
            :offset="workflowDefsOffset"
            :loading="loadingWorkflowDefs"
            @refresh="fetchWorkflowDefinitions"
            @select="openWorkflowDetail"
            @pageChange="(o) => { workflowDefsOffset = o; fetchWorkflowDefinitions() }"
          />
        </template>

        <!-- Workflow Detail (v2.0) -->
        <template v-else-if="currentNav === 'workflow-detail'">
          <WorkflowDetail
            v-if="selectedWorkflowDef"
            :workflow="selectedWorkflowDef"
            :runs="selectedWorkflowRuns"
            :versions="workflowVersions"
            :loadingVersions="loadingWorkflowVersions"
            :rollingBack="rollingBackWorkflow"
            @back="backToWorkflows"
            @startRun="handleStartWorkflowRun"
            @selectRun="handleSelectWorkflowRun"
            @loadVersions="handleLoadWorkflowVersions"
            @rollback="handleWorkflowRollback"
          />
        </template>

        <!-- Audit Log (v3.0) -->
        <template v-else-if="currentNav === 'audit'">
          <AuditLogPanel
            :logs="auditLogs"
            :total="auditTotal"
            :limit="auditLimit"
            :offset="auditOffset"
            :loading="loadingAudit"
            @refresh="fetchAuditLogs"
            @filterChange="handleAuditFilterChange"
            @pageChange="handleAuditPageChange"
          />
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
import { useI18n } from 'vue-i18n'
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
import KnowledgeSearch from './components/KnowledgeSearch.vue'
import ReviewDashboard from './components/ReviewDashboard.vue'
import ProviderPanel from './components/ProviderPanel.vue'
import CostDashboard from './components/CostDashboard.vue'
import GuardrailsPanel from './components/GuardrailsPanel.vue'
import RunList from './components/RunList.vue'
import RunDetail from './components/RunDetail.vue'
import ApprovalInbox from './components/ApprovalInbox.vue'
import EvalDashboard from './components/EvalDashboard.vue'
import ConfigCompare from './components/ConfigCompare.vue'
import WorkflowList from './components/WorkflowList.vue'
import WorkflowDetail from './components/WorkflowDetail.vue'
import FailedEventsPanel from './components/FailedEventsPanel.vue'
import AuditLogPanel from './components/AuditLogPanel.vue'
import HealthMatrix from './components/HealthMatrix.vue'
import { API_BASE } from './config'
import type { Task, Log, HistoryItem, SessionDetailData, TraceRun, TraceSpan, RcaReport, RunbookReport, OverviewSnapshot, AlertItem, WorkflowRun, WorkflowSpan, WorkflowRuntime, ApprovalItem, EvalSummaryData, ConfigVersionItem, ConfigCompareData, WorkflowDefinition, WorkflowRunDetail, WorkflowVersionHistoryItem, FailedEventItem, ConnectorConfig } from './types'
import { useToast } from './composables/useToast'
import { NAV_TO_HASH, HASH_TO_NAV, LEGACY_NAV_IDS } from './composables/useNavigation'
import { useNavigation } from './composables/useNavigation'
import { fetchJSON, fetchOptional, extractError } from './composables/useApi'
import { listRuns, getTrace, listRuntimes, listConnectors, replayFailedEvent } from './composables/useWorkflowApi'
import { listApprovals, approveApproval, rejectApproval, batchApprove, batchReject } from './composables/useApprovalApi'
import { generateRca, getLatestRca, generateRunbook, getLatestRunbook, exportArtifact } from './composables/useRunAnalysisApi'
import { getEvalSummary, listConfigVersions, compareConfigs } from './composables/useEvalApi'
import { listWorkflowDefinitions, getWorkflowDefinition, listWorkflowRuns, startWorkflowRun, listWorkflowVersions, rollbackWorkflow } from './composables/useWorkflowOrchestrationApi'
import { listAuditLogs } from './composables/useAuditApi'
import type { AuditLogEntry } from './composables/useAuditApi'

// i18n
const { t } = useI18n()

// Navigation state
const { navTitleMap } = useNavigation()
const currentNav = ref('dashboard')

function isLegacyNav(navId: string): boolean {
  return LEGACY_NAV_IDS.has(navId)
}

function handleNavChange(navId: string) {
  currentNav.value = navId
  if (NAV_TO_HASH[navId]) window.location.hash = NAV_TO_HASH[navId]
  if (navId === 'runs') {
    void fetchWorkflowRuns()
    if (workflowRuntimes.value.length === 0) void fetchWorkflowRuntimes()
  }
  if (navId === 'approvals') {
    void fetchApprovals()
  }
  if (navId === 'connectors') {
    void loadConnectorItems()
  }
  if (navId === 'eval') {
    void fetchEvalSummary()
    void fetchConfigVersions()
  }
  if (navId === 'config-compare') {
    void fetchConfigVersions()
  }
  if (navId === 'workflows') {
    void fetchWorkflowDefinitions()
  }
  if (navId === 'audit') {
    void fetchAuditLogs()
  }
  if (navId === 'system') {
    void fetchHealth()
  }
  if (navId === 'tasks') {
    void fetchTasks()
  }
  if (navId === 'logs') {
    void fetchLogs()
  }
  if (navId === 'history') {
    void fetchHistory()
  }
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

// Workflow runs state (v1.0)
const workflowRuns = ref<WorkflowRun[]>([])
const workflowRuntimes = ref<WorkflowRuntime[]>([])
const connectorTypeOptions = ref<string[]>([])
const workflowRunsTotal = ref(0)
const workflowRunsLimit = ref(50)
const workflowRunsOffset = ref(0)
const workflowRunsStatusFilter = ref('')
const workflowRunsRuntimeFilter = ref('')
const loadingWorkflowRuns = ref(false)
const selectedRunId = ref('')
const selectedRun = ref<WorkflowRun | null>(null)
const selectedRunSpans = ref<WorkflowSpan[]>([])
const loadingRunDetail = ref(false)
const runDetailError = ref<string | null>(null)

// Approval Inbox state (v1.1)
const approvalItems = ref<ApprovalItem[]>([])
const approvalTotal = ref(0)
const approvalLimit = ref(50)
const approvalOffset = ref(0)
const approvalStatusFilter = ref('')
const loadingApprovals = ref(false)
const approvalActionLoading = ref(false)

// Eval state
const evalSummary = ref<EvalSummaryData>({
  total: 0, passed: 0, failed: 0,
  by_runtime: [], by_config_version: [], trend: [],
})
const loadingEval = ref(false)
const configVersions = ref<ConfigVersionItem[]>([])
const configCompareResult = ref<ConfigCompareData | null>(null)
const loadingConfigCompare = ref(false)

// Workflow Orchestration state (v2.0)
const workflowDefinitions = ref<WorkflowDefinition[]>([])
const workflowDefsTotal = ref(0)
const workflowDefsLimit = ref(50)
const workflowDefsOffset = ref(0)
const loadingWorkflowDefs = ref(false)
const selectedWorkflowDef = ref<WorkflowDefinition | null>(null)
const selectedWorkflowRuns = ref<WorkflowRunDetail[]>([])
const selectedWorkflowRunDetail = ref<WorkflowRunDetail | null>(null)
const loadingWorkflowDetail = ref(false)
const workflowVersions = ref<WorkflowVersionHistoryItem[]>([])
const loadingWorkflowVersions = ref(false)
const rollingBackWorkflow = ref(false)

// Failed Events state (OPT-54/58)
const failedEvents = ref<FailedEventItem[]>([])
const failedEventsTotal = ref(0)
const failedEventsLimit = ref(50)
const failedEventsOffset = ref(0)
const failedEventsCursor = ref<string | null>(null)
const failedEventsHasMore = ref(false)
const failedEventsCursorStack = ref<string[]>([])
const failedEventsConnectorId = ref('')
const loadingFailedEvents = ref(false)
const replayingFailedEventId = ref('')
const connectorItems = ref<ConnectorConfig[]>([])

// Audit Log state (v3.0)
const auditLogs = ref<AuditLogEntry[]>([])
const auditTotal = ref(0)
const auditLimit = ref(50)
const auditOffset = ref(0)
const auditFilters = ref({ actor_type: '', actor_id: '', action: '', resource_type: '', resource_id: '' })
const loadingAudit = ref(false)

// Health Matrix state (v3.0)
const healthData = ref<any>(null)
const metricsData = ref<any>(null)
const loadingHealth = ref(false)

// Loading states
const loadingTasks = ref(false)
const loadingLogs = ref(false)
const loadingHistory = ref(false)
const loadingOverview = ref(false)
const loadingAlerts = ref(false)
const loadingSessionDetail = ref(false)
const loadingRca = ref(false)
const loadingRunbook = ref(false)
const exportingMarkdown = ref(false)

// Toast notifications (shared composable)
const { toasts, addToast, removeToast } = useToast()

// Terminal tab management
interface TerminalTab {
  id: string
  name: string
  sessionId: string  // unique per tab, passed to Terminal via prop
}

function createTerminalSession(): string {
  const sid = Math.random().toString(36).substring(2, 10)
  return sid
}

localStorage.removeItem('hermes_terminal_session_id')

const terminalTabs = ref<TerminalTab[]>([{
  id: 'terminal-1',
  name: 'Terminal 1',
  sessionId: createTerminalSession(),
}])
const activeTerminalId = ref<string>('terminal-1')
let terminalCounter = 1

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

function closeTerminal(idx: number) {
  if (terminalTabs.value.length === 1) return // Keep at least one
  const tab = terminalTabs.value[idx]
  if (!tab) return

  if (activeTerminalId.value === tab.id) {
    const nextTab = terminalTabs.value[idx + 1] || terminalTabs.value[idx - 1]
    if (nextTab) activeTerminalId.value = nextTab.id
  }

  terminalTabs.value.splice(idx, 1)

  void fetch(`${API_BASE}/api/terminal/sessions/${encodeURIComponent(tab.sessionId)}`, {
      method: 'DELETE',
    })
    .catch(() => {
      addToast('warning', `Terminal session close request failed, tab removed locally`)
    })
}

function onTerminalConnected() {
  // Terminal connected successfully
}


// Polling interval
let statusPollInterval: number | null = null
let eventSource: EventSource | null = null

// Actions
function handlePause(taskId: string) {
  addToast('info', `Pause task: ${taskId.slice(0, 8)}`)
}

function handleCancel(taskId: string) {
  addToast('warning', `Cancel task: ${taskId.slice(0, 8)}`)
}

function handleViewDetails(item: HistoryItem) {
  openSessionDetail(item.task_id, item)
}

function handleReRunTask(item: HistoryItem) {
  addToast('info', `Re-run: ${item.name}`)
}

// API calls
async function fetchHermesStatus() {
  try {
    const data = await fetchJSON<any>(`${API_BASE}/health`)
    hermesStatus.value = {
      ...data,
      gateway_running: data.status === 'healthy',
    }
    initError.value = null
  } catch (e) {
    if (!hermesStatus.value) {
      initError.value = `Cannot connect to backend (${API_BASE}). Ensure the API server is running.`
    }
    hermesStatus.value = null
  }
}

async function fetchTasks() {
  loadingTasks.value = true
  tasks.value = []
  loadingTasks.value = false
}

async function fetchLogs() {
  loadingLogs.value = true
  logs.value = []
  loadingLogs.value = false
}

async function fetchHistory() {
  loadingHistory.value = true
  history.value = []
  loadingHistory.value = false
}

async function fetchOverviewSnapshot() {
  loadingOverview.value = true
  const [
    health,
    evalSummary,
    metrics,
  ] = await Promise.all([
    fetchOptional<Record<string, any>>(`${API_BASE}/health`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/agent/evals/summary`),
    fetchOptional<Record<string, any>>(`${API_BASE}/api/metrics`),
  ])
  overviewSnapshot.value = {
    health,
    analytics: metrics,
    evalSummary,
    modelInfo: null,
    config: null,
    skills: null,
    cronJobs: null,
    plugins: null,
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
    selectedSessionDetail.value = {
      task_id: taskId,
      name: selectedHistoryItem.value?.name || `Run ${taskId.slice(0, 8)}`,
      status: selectedHistoryItem.value?.status || 'unknown',
      messages: [],
      message_count: selectedHistoryItem.value?.message_count || 0,
      logs: [],
    }
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
    addToast('success', 'RCA analysis generated')
  } catch (e) {
    addToast('error', `RCA analysis failed: ${extractError(e)}`)
  } finally {
    loadingRca.value = false
  }
}

async function generateSessionRunbook() {
  if (!selectedSessionId.value || loadingRunbook.value) return
  await generateRunbookForSession(selectedSessionId.value)
}

async function generateRunbookForSession(sessionId: string) {
  if (!sessionId || loadingRunbook.value) return
  loadingRunbook.value = true
  try {
    const data = await fetchJSON<{ runbook: RunbookReport }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}/runbook`,
      { method: 'POST' }
    )
    if (selectedSessionId.value === sessionId) {
      selectedRunbook.value = data.runbook
      await fetchLatestRca(sessionId)
      await fetchLatestTrace(sessionId)
    }
    addToast('success', 'Runbook generated')
  } catch (e) {
    addToast('error', `Runbook generation failed: ${extractError(e)}`)
  } finally {
    loadingRunbook.value = false
  }
}

async function exportSessionMarkdown() {
  if (!selectedSessionId.value || exportingMarkdown.value) return
  exportingMarkdown.value = true
  try {
    const data = await fetchJSON<{ export: { path: string } }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(selectedSessionId.value)}/export`,
      { method: 'POST' }
    )
    addToast('success', `Markdown exported: ${data.export.path}`)
  } catch (e) {
    addToast('error', `Markdown export failed: ${extractError(e)}`)
  } finally {
    exportingMarkdown.value = false
  }
}

async function confirmRunbookStep(stepId: string) {
  if (!selectedSessionId.value || !selectedRunbook.value) return
  try {
    const data = await fetchJSON<{ step: { step_id: string; status: string }; runbook?: RunbookReport }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(selectedSessionId.value)}/runbook/steps/${encodeURIComponent(stepId)}/confirm`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true, confirmed_by: 'dashboard' }),
      }
    )
    selectedRunbook.value = data.runbook || patchRunbookStep(selectedRunbook.value, stepId, data.step.status)
    await fetchLatestTrace(selectedSessionId.value)
    addToast('success', 'Runbook step confirmed')
  } catch (e) {
    addToast('error', `Runbook step confirmation failed: ${extractError(e)}`)
  }
}

async function executeRunbookStep(stepId: string) {
  if (!selectedSessionId.value || !selectedRunbook.value) return
  try {
    const data = await fetchJSON<{ step: { step_id: string; status: string }; runbook?: RunbookReport; message?: string }>(
      `${API_BASE}/api/sessions/${encodeURIComponent(selectedSessionId.value)}/runbook/steps/${encodeURIComponent(stepId)}/execute`,
      { method: 'POST' }
    )
    selectedRunbook.value = data.runbook || patchRunbookStep(selectedRunbook.value, stepId, data.step.status)
    await fetchLatestTrace(selectedSessionId.value)
    addToast(data.step.status === 'blocked_unsafe' ? 'warning' : 'success', data.message || 'Runbook step executed')
  } catch (e) {
    addToast('error', `Runbook step execution failed: ${extractError(e)}`)
  }
}

function patchRunbookStep(runbook: RunbookReport, stepId: string, status: string): RunbookReport {
  return {
    ...runbook,
    execution_steps: (runbook.execution_steps || []).map(step =>
      step.step_id === stepId ? { ...step, status } : step
    ),
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

// ---------------------------------------------------------------------------
// Workflow Runs (v1.0)
// ---------------------------------------------------------------------------

async function fetchWorkflowRuntimes() {
  try {
    workflowRuntimes.value = await listRuntimes()
  } catch {
    // runtimes are optional for filtering
  }
  try {
    const connectors = await listConnectors()
    const types = [...new Set(connectors.items.map(c => c.connector_type))]
    connectorTypeOptions.value = types
  } catch {
    // connectors are optional for filtering
  }
}

async function fetchWorkflowRuns() {
  loadingWorkflowRuns.value = true
  try {
    const data = await listRuns({
      runtime_id: workflowRunsRuntimeFilter.value || undefined,
      status: workflowRunsStatusFilter.value || undefined,
      limit: workflowRunsLimit.value,
      offset: workflowRunsOffset.value,
    })
    workflowRuns.value = data.items
    workflowRunsTotal.value = data.total
    workflowRunsOffset.value = data.offset
  } catch (e) {
    addToast('error', `Failed to load workflow runs: ${extractError(e)}`)
  } finally {
    loadingWorkflowRuns.value = false
  }
}

function handleWorkflowFilterChange(filters: { status: string; runtime_id: string; connector_type: string }) {
  workflowRunsStatusFilter.value = filters.status
  workflowRunsRuntimeFilter.value = filters.runtime_id
  workflowRunsOffset.value = 0
  void fetchWorkflowRuns()
}

function handleWorkflowPageChange(offset: number) {
  workflowRunsOffset.value = offset
  void fetchWorkflowRuns()
}

async function openRunDetail(runId: string) {
  selectedRunId.value = runId
  selectedRun.value = null
  selectedRunSpans.value = []
  runDetailError.value = null
  currentNav.value = 'run-detail'
  window.location.hash = `#/runs/${encodeURIComponent(runId)}`
  await fetchRunDetail(runId)
}

async function fetchRunDetail(runId: string) {
  loadingRunDetail.value = true
  runDetailError.value = null
  selectedRcaReport.value = null
  selectedRunbook.value = null
  try {
    const trace = await getTrace(runId)
    selectedRun.value = trace.run
    selectedRunSpans.value = trace.spans
  } catch (e: unknown) {
    const err = e as { status?: number; detail?: string }
    runDetailError.value = err.detail || `Failed to load run ${runId}`
  } finally {
    loadingRunDetail.value = false
  }
  // Load existing RCA and Runbook (non-blocking)
  getLatestRca(runId).then(r => { selectedRcaReport.value = r }).catch(() => {})
  getLatestRunbook(runId).then(r => { selectedRunbook.value = r }).catch(() => {})
}

function refreshRunDetail() {
  if (selectedRunId.value) void fetchRunDetail(selectedRunId.value)
}

function backToRuns() {
  selectedRunId.value = ''
  selectedRun.value = null
  selectedRunSpans.value = []
  runDetailError.value = null
  selectedRcaReport.value = null
  selectedRunbook.value = null
  handleNavChange('runs')
}

// RCA / Runbook handlers (v1.2)
async function handleAnalyzeRca() {
  if (!selectedRunId.value) return
  loadingRca.value = true
  try {
    selectedRcaReport.value = await generateRca(selectedRunId.value)
  } catch (e: unknown) {
    addToast('error', `RCA analysis failed: ${extractError(e)}`)
  } finally {
    loadingRca.value = false
  }
}

async function handleGenerateRunbook() {
  if (!selectedRunId.value) return
  loadingRunbook.value = true
  try {
    selectedRunbook.value = await generateRunbook(selectedRunId.value)
  } catch (e: unknown) {
    addToast('error', `Runbook generation failed: ${extractError(e)}`)
  } finally {
    loadingRunbook.value = false
  }
}

async function handleExportRca() {
  if (!selectedRunId.value) return
  try {
    const result = await exportArtifact(selectedRunId.value, 'rca')
    addToast('success', `RCA exported: ${result.title}`)
  } catch (e: unknown) {
    addToast('error', `Export failed: ${extractError(e)}`)
  }
}

async function handleExportRunbook() {
  if (!selectedRunId.value) return
  try {
    const result = await exportArtifact(selectedRunId.value, 'runbook')
    addToast('success', `Runbook exported: ${result.title}`)
  } catch (e: unknown) {
    addToast('error', `Export failed: ${extractError(e)}`)
  }
}

// ---------------------------------------------------------------------------
// Approval Inbox (v1.1)
// ---------------------------------------------------------------------------

async function fetchApprovals() {
  loadingApprovals.value = true
  try {
    const data = await listApprovals({
      status: approvalStatusFilter.value || undefined,
      limit: approvalLimit.value,
      offset: approvalOffset.value,
    })
    approvalItems.value = data.items
    approvalTotal.value = data.total
    approvalOffset.value = data.offset
  } catch {
    addToast('error', 'Failed to load approvals')
  } finally {
    loadingApprovals.value = false
  }
}

function handleApprovalFilterChange(status: string) {
  approvalStatusFilter.value = status
  approvalOffset.value = 0
  void fetchApprovals()
}

function handleApprovalPageChange(offset: number) {
  approvalOffset.value = offset
  void fetchApprovals()
}

async function handleApprove(id: string) {
  approvalActionLoading.value = true
  try {
    await approveApproval(id)
    addToast('success', 'Approval approved')
    await fetchApprovals()
  } catch (e) {
    addToast('error', `Failed to approve: ${extractError(e)}`)
  } finally {
    approvalActionLoading.value = false
  }
}

async function handleReject(id: string) {
  approvalActionLoading.value = true
  try {
    await rejectApproval(id)
    addToast('success', 'Approval rejected')
    await fetchApprovals()
  } catch (e) {
    addToast('error', `Failed to reject: ${extractError(e)}`)
  } finally {
    approvalActionLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Audit Log (v3.0)
// ---------------------------------------------------------------------------

async function fetchAuditLogs() {
  loadingAudit.value = true
  try {
    const data = await listAuditLogs({
      actor_type: auditFilters.value.actor_type || undefined,
      actor_id: auditFilters.value.actor_id || undefined,
      action: auditFilters.value.action || undefined,
      resource_type: auditFilters.value.resource_type || undefined,
      resource_id: auditFilters.value.resource_id || undefined,
      limit: auditLimit.value,
      offset: auditOffset.value,
    })
    auditLogs.value = data.logs
    auditTotal.value = data.total
  } catch {
    addToast('error', 'Failed to load audit logs')
  } finally {
    loadingAudit.value = false
  }
}

function handleAuditFilterChange(filters: { actor_type: string; actor_id: string; action: string; resource_type: string; resource_id: string }) {
  auditFilters.value = { ...filters }
  auditOffset.value = 0
  void fetchAuditLogs()
}

function handleAuditPageChange(offset: number) {
  auditOffset.value = offset
  void fetchAuditLogs()
}

async function fetchHealth() {
  loadingHealth.value = true
  try {
    const [health, metrics] = await Promise.all([
      fetchJSON(`${API_BASE}/health`),
      fetchJSON(`${API_BASE}/api/metrics`).catch(() => null),
    ])
    healthData.value = health
    metricsData.value = metrics
  } catch {
    addToast('error', 'Failed to load health status')
    healthData.value = null
    metricsData.value = null
  } finally {
    loadingHealth.value = false
  }
}

// ---------------------------------------------------------------------------
// Eval / Config Version
// ---------------------------------------------------------------------------

async function fetchEvalSummary() {
  loadingEval.value = true
  try {
    evalSummary.value = await getEvalSummary()
  } catch {
    addToast('error', 'Failed to load eval summary')
  } finally {
    loadingEval.value = false
  }
}

async function fetchConfigVersions() {
  try {
    const data = await listConfigVersions()
    configVersions.value = data.items
  } catch {
    addToast('error', 'Failed to load config versions')
  }
}

async function handleConfigCompare(beforeId: string, afterId: string) {
  loadingConfigCompare.value = true
  configCompareResult.value = null
  try {
    configCompareResult.value = await compareConfigs({
      before_version_id: beforeId,
      after_version_id: afterId,
    })
  } catch {
    addToast('error', 'Failed to compare configs')
  } finally {
    loadingConfigCompare.value = false
  }
}

// ---------------------------------------------------------------------------
// Workflow Orchestration (v2.0)
// ---------------------------------------------------------------------------

async function fetchWorkflowDefinitions() {
  loadingWorkflowDefs.value = true
  try {
    const data = await listWorkflowDefinitions({
      limit: workflowDefsLimit.value,
      offset: workflowDefsOffset.value,
    })
    workflowDefinitions.value = data.items
    workflowDefsTotal.value = data.total
  } catch {
    addToast('error', 'Failed to load workflow definitions')
  } finally {
    loadingWorkflowDefs.value = false
  }
}

async function openWorkflowDetail(wf: WorkflowDefinition) {
  selectedWorkflowDef.value = wf
  selectedWorkflowRuns.value = []
  workflowVersions.value = []
  currentNav.value = 'workflow-detail'
  window.location.hash = `#/workflows/${encodeURIComponent(wf.id)}`
  loadingWorkflowDetail.value = true
  try {
    const [detail, runsData] = await Promise.all([
      getWorkflowDefinition(wf.id),
      listWorkflowRuns(wf.id),
    ])
    selectedWorkflowDef.value = detail
    selectedWorkflowRuns.value = runsData.items
    void handleLoadWorkflowVersions()
  } catch {
    addToast('error', 'Failed to load workflow detail')
  } finally {
    loadingWorkflowDetail.value = false
  }
}

function backToWorkflows() {
  currentNav.value = 'workflows'
  window.location.hash = '#/workflows'
}

async function handleStartWorkflowRun() {
  if (!selectedWorkflowDef.value) return
  try {
    const run = await startWorkflowRun(selectedWorkflowDef.value.id, {
      input_summary: 'Manual run from dashboard',
    })
    selectedWorkflowRuns.value = [run, ...selectedWorkflowRuns.value]
    addToast('success', 'Workflow run started')
  } catch (e) {
    addToast('error', `Failed to start workflow run: ${extractError(e)}`)
  }
}

async function handleSelectWorkflowRun(run: WorkflowRunDetail) {
  selectedWorkflowRunDetail.value = run
}

async function handleLoadWorkflowVersions() {
  if (!selectedWorkflowDef.value) return
  loadingWorkflowVersions.value = true
  try {
    const data = await listWorkflowVersions(selectedWorkflowDef.value.id)
    workflowVersions.value = data.items
  } catch {
    addToast('error', 'Failed to load version history')
  } finally {
    loadingWorkflowVersions.value = false
  }
}

async function handleWorkflowRollback(version: number) {
  if (!selectedWorkflowDef.value) return
  rollingBackWorkflow.value = true
  try {
    const updated = await rollbackWorkflow(selectedWorkflowDef.value.id, { version })
    selectedWorkflowDef.value = updated
    addToast('success', `Rolled back to v${version}`)
    await handleLoadWorkflowVersions()
  } catch {
    addToast('error', 'Failed to rollback workflow')
  } finally {
    rollingBackWorkflow.value = false
  }
}

// ---------------------------------------------------------------------------
// Failed Events (OPT-54)
// ---------------------------------------------------------------------------

async function loadConnectorItems() {
  try {
    const data = await listConnectors()
    connectorItems.value = data.items
  } catch {
    addToast('error', 'Failed to load connectors')
  }
}

async function fetchFailedEvents(connectorId?: string, cursor?: string | null) {
  const cid = connectorId || failedEventsConnectorId.value
  if (!cid) return
  failedEventsConnectorId.value = cid
  loadingFailedEvents.value = true
  try {
    const params: Record<string, string | number> = { limit: failedEventsLimit.value }
    if (cursor) {
      params.cursor = cursor
    } else {
      params.offset = failedEventsOffset.value
    }
    const searchParams = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) searchParams.set(k, String(v))
    const data = await (await import('./composables/useApi')).fetchJSON(
      `${(await import('./config')).API_BASE}/api/connectors/${encodeURIComponent(cid)}/failed-events?${searchParams}`,
    ) as { items: FailedEventItem[]; total: number; next_cursor: string | null; has_more: boolean }
    failedEvents.value = data.items
    failedEventsTotal.value = data.total
    failedEventsHasMore.value = data.has_more
    failedEventsCursor.value = data.next_cursor
  } catch {
    addToast('error', 'Failed to load failed events')
  } finally {
    loadingFailedEvents.value = false
  }
}

function handleFailedEventConnectorChange(connectorId: string) {
  failedEventsConnectorId.value = connectorId
  failedEventsOffset.value = 0
  failedEventsCursor.value = null
  failedEventsCursorStack.value = []
  void fetchFailedEvents(connectorId)
}

function handleFailedEventsNextPage() {
  if (failedEventsCursor.value) {
    failedEventsCursorStack.value.push(failedEventsCursor.value)
    failedEventsOffset.value += failedEventsLimit.value
    void fetchFailedEvents(undefined, failedEventsCursor.value)
  }
}

function handleFailedEventsPrevPage() {
  failedEventsCursorStack.value.pop()
  failedEventsOffset.value = Math.max(0, failedEventsOffset.value - failedEventsLimit.value)
  const prevCursor = failedEventsCursorStack.value.length > 0
    ? failedEventsCursorStack.value[failedEventsCursorStack.value.length - 1]
    : null
  void fetchFailedEvents(undefined, prevCursor)
}

async function handleReplayFailedEvent(eventId: string) {
  if (!failedEventsConnectorId.value) return
  replayingFailedEventId.value = eventId
  try {
    await replayFailedEvent(failedEventsConnectorId.value, eventId)
    addToast('success', 'Event replayed successfully')
    await fetchFailedEvents()
  } catch {
    addToast('error', 'Failed to replay event')
  } finally {
    replayingFailedEventId.value = ''
  }
}

function handleFailedEventPageChange(offset: number) {
  failedEventsOffset.value = offset
  void fetchFailedEvents()
}

// ---------------------------------------------------------------------------
// Batch Approvals (OPT-55)
// ---------------------------------------------------------------------------

async function handleBatchApprove(ids: string[]) {
  approvalActionLoading.value = true
  try {
    const result = await batchApprove(ids)
    addToast('success', `Batch approved: ${result.processed} processed, ${result.skipped} skipped`)
    await fetchApprovals()
  } catch {
    addToast('error', 'Batch approve failed')
  } finally {
    approvalActionLoading.value = false
  }
}

async function handleBatchReject(ids: string[]) {
  approvalActionLoading.value = true
  try {
    const result = await batchReject(ids)
    addToast('success', `Batch rejected: ${result.processed} processed, ${result.skipped} skipped`)
    await fetchApprovals()
  } catch {
    addToast('error', 'Batch reject failed')
  } finally {
    approvalActionLoading.value = false
  }
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

async function handleAlertRunbook(alert: AlertItem) {
  if (!alert.session_id) return
  await generateRunbookForSession(alert.session_id)
}

async function handleTopRefresh() {
  if (currentNav.value === 'session-detail') {
    refreshSessionDetail()
    return
  }
  if (currentNav.value === 'runs') {
    await fetchWorkflowRuns()
    return
  }
  if (currentNav.value === 'run-detail') {
    refreshRunDetail()
    return
  }
  if (currentNav.value === 'approvals') {
    await fetchApprovals()
    return
  }
  if (currentNav.value === 'tasks') {
    await fetchTasks()
    return
  }
  if (currentNav.value === 'logs') {
    await fetchLogs()
    return
  }
  if (currentNav.value === 'history') {
    await fetchHistory()
    return
  }
  await refreshAll()
}

async function refreshAll() {
  isRefreshing.value = true
  await Promise.all([
    fetchHermesStatus(),
    fetchWorkflowRuns(),
    fetchWorkflowRuntimes(),
    fetchWorkflowDefinitions(),
    fetchApprovals(),
    fetchEvalSummary(),
    fetchOverviewSnapshot(),
    fetchAlerts(),
  ])
  isRefreshing.value = false
  addToast('success', 'Data refreshed')
}

// retryInit removed - unused

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
        addToast('error', data.message || 'SSE error')
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
      addToast('error', `SSE connection failed, retry stopped. Please refresh the page.`)
      return
    }

    const delay = getReconnectDelay(reconnectAttempts.value)
    reconnectAttempts.value++

    if (!isReconnecting.value) {
      isReconnecting.value = true
      addToast('warning', `SSE disconnected, reconnecting in ${Math.round(delay / 1000)}s...`)
    }

    setTimeout(connectSSE, delay)
  }
}

onMounted(async () => {
  await refreshAll()
  statusPollInterval = window.setInterval(fetchHermesStatus, 30000)
  connectSSE()

  // Sync hash route to currentNav so browser back/forward and direct URL work
  const handleHashChange = () => {
    const sessionMatch = window.location.hash.match(/^#\/sessions\/(.+)$/)
    if (sessionMatch) {
      const taskId = decodeURIComponent(sessionMatch[1])
      if (selectedSessionId.value !== taskId || currentNav.value !== 'session-detail') {
        openSessionDetail(taskId)
      }
      return
    }
    const runMatch = window.location.hash.match(/^#\/runs\/(.+)$/)
    if (runMatch) {
      const runId = decodeURIComponent(runMatch[1])
      if (selectedRunId.value !== runId || currentNav.value !== 'run-detail') {
        openRunDetail(runId)
      }
      return
    }
    const baseHash = window.location.hash.split('?')[0]
    const nav = HASH_TO_NAV[baseHash]
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

/* Legacy Deprecation Banner */
.legacy-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--warning-bg, rgba(255, 193, 7, 0.1));
  border: 1px solid var(--warning-color, #ffc107);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-secondary);
}

.legacy-banner-icon {
  font-size: 16px;
  flex-shrink: 0;
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

.terminal-pane {
  flex: 1;
  min-height: 0;
  height: 100%;
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
