<template>
  <section class="system-config">
    <div class="system-header">
      <div>
        <h2>系统配置中心</h2>
        <p>运行时、工具策略、导出和后台进程</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '同步中' : '刷新' }}
      </button>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="summary-grid">
      <div class="summary-card">
        <span>模型</span>
        <strong>{{ modelName }}</strong>
        <small>{{ modelProvider }}</small>
      </div>
      <div class="summary-card">
        <span>Runtimes</span>
        <strong>{{ runtimes.length }}</strong>
        <small>执行运行时</small>
      </div>
      <div class="summary-card">
        <span>Workers</span>
        <strong>{{ workers.length }}</strong>
        <small>后台进程</small>
      </div>
      <div class="summary-card">
        <span>Tools</span>
        <strong>{{ tools.length }}</strong>
        <small>Agent 可调用能力</small>
      </div>
      <div class="summary-card">
        <span>Guardrails</span>
        <strong>{{ guardrails.length }}</strong>
        <small>工具门禁策略</small>
      </div>
      <div class="summary-card">
        <span>Exports</span>
        <strong>{{ exportFiles.length }}</strong>
        <small>Markdown 文件</small>
      </div>
    </div>

    <div class="config-grid">
      <div class="config-section">
        <div class="section-title">控制面配置</div>
        <div class="kv-list">
          <div v-for="item in configEntries" :key="item.key" class="kv-row">
            <span>{{ item.key }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <div v-if="configEntries.length === 0" class="empty">暂无控制面数据</div>
        </div>
      </div>

      <div class="config-section">
        <div class="section-title">运行时信息</div>
        <div class="kv-list">
          <div v-for="item in modelEntries" :key="item.key" class="kv-row">
            <span>{{ item.key }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <div v-if="modelEntries.length === 0" class="empty">暂无运行时数据</div>
        </div>
      </div>
    </div>

    <div class="approval-section">
      <div class="section-title">Agent 性能趋势</div>
      <div class="trend-summary">
        <div>
          <span>总运行</span>
          <strong>{{ evalSummary?.total_runs || 0 }}</strong>
        </div>
        <div>
          <span>成功率</span>
          <strong>{{ formatPercent(evalSummary?.success_rate || 0) }}</strong>
        </div>
        <div>
          <span>平均耗时</span>
          <strong>{{ evalSummary?.avg_duration_seconds || 0 }}s</strong>
        </div>
      </div>
      <div v-if="evalTrend.length > 0" class="trend-list">
        <div v-for="point in evalTrend" :key="point.date" class="trend-row">
          <span>{{ point.date }}</span>
          <div class="trend-bar">
            <i :style="{ width: trendWidth(point.runs) }"></i>
          </div>
          <strong>{{ point.runs }} 次 / {{ formatPercent(point.success_rate) }}</strong>
          <small>{{ point.errors }} 错误 · {{ point.avg_duration_seconds }}s</small>
        </div>
      </div>
      <div v-else class="empty">暂无 Agent 运行趋势</div>
    </div>

    <div class="approval-section">
      <div class="section-title">待审批 Guardrail</div>
      <div v-if="approvalEvents.length > 0" class="approval-list">
        <div v-for="event in approvalEvents" :key="event.event_id" class="approval-item" :class="event.status">
          <div class="approval-main">
            <strong>{{ event.tool }}</strong>
            <span>{{ event.risk }} / {{ event.status }}</span>
            <p>{{ event.description }}</p>
          </div>
          <div class="approval-actions">
            <button
              class="approve-btn"
              :disabled="event.status !== 'pending' || resolvingId === event.event_id"
              @click="resolveApproval(event.event_id, 'approve')"
            >
              批准
            </button>
            <button
              class="reject-btn"
              :disabled="event.status !== 'pending' || resolvingId === event.event_id"
              @click="resolveApproval(event.event_id, 'reject')"
            >
              拒绝
            </button>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无待审批工具调用</div>
    </div>

    <div class="approval-section">
      <div class="section-title">Markdown 同步</div>
      <div class="export-target">
        <span>导出目录</span>
        <strong>{{ exportsInfo?.export_dir || '未确认' }}</strong>
      </div>
      <div v-if="exportFiles.length > 0" class="export-list">
        <div v-for="file in exportFiles" :key="file.path" class="export-item">
          <strong>{{ file.filename }}</strong>
          <span>{{ formatBytes(file.bytes) }} / {{ formatDate(file.updated_at) }}</span>
        </div>
      </div>
      <div v-else class="empty">暂无 Markdown 导出文件</div>
    </div>

    <div class="resource-grid">
      <ResourceList title="Runtimes" :items="runtimes" empty-text="暂无 Runtimes" />
      <ResourceList title="Tools" :items="tools" empty-text="暂无 Tools" />
      <ResourceList title="Guardrails" :items="guardrails" empty-text="暂无 Guardrails" />
      <ResourceList title="Workers" :items="workers" empty-text="暂无 Workers" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { API_BASE } from '../config'
import { formatDate, formatBytes, formatPercent } from '../composables/useFormatters'

interface ResourceItem {
  id?: string
  name?: string
  title?: string
  description?: string
  enabled?: boolean
  status?: string
  schedule?: string
  risk?: string
  decision?: string
  type?: string
  version?: string
}

interface ApprovalEvent {
  event_id: string
  tool: string
  risk: string
  description: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  updated_at: string
}

interface ExportFile {
  filename: string
  path: string
  bytes: number
  updated_at: string
}

interface ExportsInfo {
  export_dir: string
  exists: boolean
  files: ExportFile[]
  count: number
}

interface EvalTrendPoint {
  date: string
  runs: number
  errors: number
  success_rate: number
  avg_duration_seconds: number
}

interface EvalSummary {
  total_runs: number
  success_rate: number
  avg_duration_seconds: number
  trend: EvalTrendPoint[]
}

const loading = ref(false)
const error = ref('')
const config = ref<Record<string, any> | null>(null)
const modelInfo = ref<Record<string, any> | null>(null)
const runtimes = ref<ResourceItem[]>([])
const tools = ref<ResourceItem[]>([])
const guardrails = ref<ResourceItem[]>([])
const approvalEvents = ref<ApprovalEvent[]>([])
const workers = ref<ResourceItem[]>([])
const resolvingId = ref('')
const exportsInfo = ref<ExportsInfo | null>(null)
const evalSummary = ref<EvalSummary | null>(null)

const modelName = computed(() => modelInfo.value?.primary_runtime || modelInfo.value?.name || '未确认')
const modelProvider = computed(() => modelInfo.value?.runtime_type || modelInfo.value?.status || '运行时')

const configEntries = computed(() => toEntries(config.value, 8))
const modelEntries = computed(() => toEntries(modelInfo.value, 8))
const exportFiles = computed(() => exportsInfo.value?.files || [])
const evalTrend = computed(() => evalSummary.value?.trend || [])
const maxTrendRuns = computed(() => Math.max(1, ...evalTrend.value.map(point => point.runs)))

async function load() {
  loading.value = true
  error.value = ''
  const [healthData, runtimesData, toolsData, guardrailsData, exportsData, evalData, metricsData] = await Promise.all([
    fetchOptional<Record<string, any>>('/health'),
    fetchOptional<Record<string, any>>('/api/runtimes'),
    fetchOptional<Record<string, any>>('/api/agent/tools'),
    fetchOptional<Record<string, any>>('/api/agent/guardrails'),
    fetchOptional<ExportsInfo>('/api/exports?limit=8'),
    fetchOptional<EvalSummary>('/api/agent/evals/summary'),
    fetchOptional<Record<string, any>>('/api/metrics'),
  ])

  config.value = buildControlPlaneConfig(healthData, metricsData)
  modelInfo.value = buildRuntimeInfo(runtimesData)
  runtimes.value = normalizeCollection(runtimesData, ['items', 'runtimes'])
  tools.value = normalizeCollection(toolsData, ['tools'])
  guardrails.value = normalizeCollection(guardrailsData, ['tool_policies'])
  approvalEvents.value = normalizeCollection(guardrailsData, ['approval_events']) as ApprovalEvent[]
  workers.value = normalizeWorkers(healthData?.workers)
  exportsInfo.value = exportsData
  evalSummary.value = evalData
  if (!healthData && runtimes.value.length === 0 && tools.value.length === 0 && guardrails.value.length === 0 && workers.value.length === 0) {
    error.value = '暂时无法读取控制面配置，请确认后端 API 可达。'
  }
  loading.value = false
}

async function resolveApproval(eventId: string, action: 'approve' | 'reject') {
  resolvingId.value = eventId
  try {
    const res = await fetch(`${API_BASE}/api/agent/guardrails/${eventId}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolved_by: 'dashboard' }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await load()
  } catch (e) {
    error.value = '审批操作失败，请刷新后重试。'
  } finally {
    resolvingId.value = ''
  }
}

async function fetchOptional<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`)
    if (!res.ok) return null
    return res.json()
  } catch (e) {
    return null
  }
}

function normalizeCollection(value: Record<string, any> | null, keys: string[]): ResourceItem[] {
  if (!value) return []
  if (Array.isArray(value)) return value
  for (const key of keys) {
    if (Array.isArray(value[key])) return value[key]
  }
  return []
}

function normalizeWorkers(value: Record<string, any> | null | undefined): ResourceItem[] {
  if (!value || typeof value !== 'object') return []
  return Object.entries(value).map(([name, worker]) => {
    const item = (worker || {}) as Record<string, any>
    return {
      id: name,
      name,
      status: item.status,
      description: item.worker_id ? `worker_id=${item.worker_id}` : undefined,
      version: item.version,
    }
  })
}

function buildControlPlaneConfig(health: Record<string, any> | null, metrics: Record<string, any> | null): Record<string, any> | null {
  if (!health && !metrics) return null
  return {
    service: health?.service,
    version: health?.version,
    status: health?.status,
    database: health?.database?.status,
    migration: health?.database?.migration_version,
    runs_total: metrics?.runs?.total,
    running: metrics?.runs?.running,
  }
}

function buildRuntimeInfo(value: Record<string, any> | null): Record<string, any> | null {
  const items = normalizeCollection(value, ['items', 'runtimes'])
  if (items.length === 0) return null
  const first = items[0] as Record<string, any>
  return {
    primary_runtime: first.name || first.id,
    runtime_type: first.type,
    status: first.status || 'available',
    total_runtimes: items.length,
  }
}

function toEntries(value: Record<string, any> | null, limit: number) {
  if (!value) return []
  return Object.entries(value)
    .filter(([, entryValue]) => typeof entryValue !== 'object' || entryValue === null)
    .slice(0, limit)
    .map(([key, entryValue]) => ({
      key,
      value: entryValue === null || entryValue === undefined ? 'N/A' : String(entryValue),
    }))
}

function trendWidth(runs: number): string {
  return `${Math.max(8, Math.round((runs / maxTrendRuns.value) * 100))}%`
}

const ResourceList = defineComponent({
  props: {
    title: { type: String, required: true },
    items: { type: Array as () => ResourceItem[], required: true },
    emptyText: { type: String, required: true },
  },
  setup(props) {
    return () => h('div', { class: 'resource-section' }, [
      h('div', { class: 'section-title' }, props.title),
      props.items.length > 0
        ? h('div', { class: 'resource-list' }, props.items.slice(0, 12).map((item, idx) =>
          h('div', { class: 'resource-item', key: item.id || item.name || idx }, [
            h('strong', item.name || item.title || item.id || item.risk || `Item ${idx + 1}`),
            h('span', item.description || item.schedule || item.decision || item.risk || item.status || item.type || (item.enabled === false ? 'disabled' : 'enabled')),
          ])
        ))
        : h('div', { class: 'empty' }, props.emptyText),
    ])
  },
})

onMounted(load)
</script>

<style scoped>
.system-config {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.system-header,
.summary-card,
.config-section,
.resource-section,
.approval-section,
.error-box {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.approval-section {
  padding: 20px 24px;
}

.approval-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.approval-item,
.export-item,
.export-target {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.approval-item.pending {
  border-color: rgba(245, 158, 11, 0.35);
}

.export-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.export-target {
  margin-top: 12px;
}

.approval-main strong,
.export-item strong,
.export-target strong {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.approval-main span,
.export-item span,
.export-target span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 800;
}

.approval-main span {
  text-transform: uppercase;
}

.approval-main p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.approval-actions {
  display: flex;
  gap: 8px;
}

.trend-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 12px;
}

.trend-summary div {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.trend-summary span,
.trend-row span,
.trend-row small {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 800;
}

.trend-summary strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 20px;
}

.trend-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.trend-row {
  display: grid;
  grid-template-columns: 88px 1fr 110px 110px;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.trend-bar {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--bg-secondary);
}

.trend-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent-color);
}

.trend-row strong {
  color: var(--text-primary);
  font-size: 12px;
  text-align: right;
}

.approve-btn,
.reject-btn {
  min-height: 32px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.approve-btn {
  border: 1px solid var(--success-color);
  background: var(--success-soft);
  color: var(--success-color);
}

.reject-btn {
  border: 1px solid var(--error-color);
  background: var(--error-soft);
  color: var(--error-color);
}

.approve-btn:disabled,
.reject-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.system-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.system-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
}

.system-header p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.summary-grid,
.config-grid,
.resource-grid {
  display: grid;
  gap: 16px;
}

.summary-grid {
  grid-template-columns: repeat(4, 1fr);
}

.config-grid {
  grid-template-columns: repeat(2, 1fr);
}

.resource-grid {
  grid-template-columns: repeat(3, 1fr);
}

.summary-card,
.config-section,
.resource-section {
  padding: 20px 24px;
}

.summary-card {
  min-height: 112px;
}

.summary-card span,
.section-title {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.summary-card strong {
  display: block;
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.summary-card small {
  color: var(--text-secondary);
  font-size: 12px;
}

.section-title {
  margin-bottom: 14px;
}

.kv-list,
.resource-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kv-row,
.resource-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.kv-row span,
.resource-item span {
  color: var(--text-secondary);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.kv-row strong,
.resource-item strong {
  color: var(--text-primary);
  font-size: 12px;
  text-align: right;
  overflow-wrap: anywhere;
}

.resource-item {
  align-items: flex-start;
  flex-direction: column;
}

.resource-item strong {
  text-align: left;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.empty,
.error-box {
  color: var(--text-secondary);
  font-size: 13px;
}

.error-box {
  padding: 16px 20px;
  border-color: rgba(239, 68, 68, 0.25);
  background: var(--error-soft);
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .summary-grid,
  .config-grid,
  .resource-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .system-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid,
  .config-grid,
  .resource-grid,
  .trend-summary {
    grid-template-columns: 1fr;
  }

  .trend-row {
    grid-template-columns: 1fr;
  }

  .trend-row strong {
    text-align: left;
  }
}
</style>
