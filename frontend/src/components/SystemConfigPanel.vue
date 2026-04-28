<template>
  <section class="system-config">
    <div class="system-header">
      <div>
        <h2>系统配置中心</h2>
        <p>模型、Hermès 配置、Skills、Plugins 和定时任务</p>
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
        <span>Skills</span>
        <strong>{{ skills.length }}</strong>
        <small>可用能力</small>
      </div>
      <div class="summary-card">
        <span>Plugins</span>
        <strong>{{ plugins.length }}</strong>
        <small>Dashboard 扩展</small>
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
        <span>Cron</span>
        <strong>{{ cronJobs.length }}</strong>
        <small>定时任务</small>
      </div>
    </div>

    <div class="config-grid">
      <div class="config-section">
        <div class="section-title">Hermès 配置</div>
        <div class="kv-list">
          <div v-for="item in configEntries" :key="item.key" class="kv-row">
            <span>{{ item.key }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <div v-if="configEntries.length === 0" class="empty">暂无配置数据</div>
        </div>
      </div>

      <div class="config-section">
        <div class="section-title">模型信息</div>
        <div class="kv-list">
          <div v-for="item in modelEntries" :key="item.key" class="kv-row">
            <span>{{ item.key }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <div v-if="modelEntries.length === 0" class="empty">暂无模型数据</div>
        </div>
      </div>
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

    <div class="resource-grid">
      <ResourceList title="Skills" :items="skills" empty-text="暂无 Skills" />
      <ResourceList title="Tools" :items="tools" empty-text="暂无 Tools" />
      <ResourceList title="Guardrails" :items="guardrails" empty-text="暂无 Guardrails" />
      <ResourceList title="Plugins" :items="plugins" empty-text="暂无 Plugins" />
      <ResourceList title="Cron Jobs" :items="cronJobs" empty-text="暂无定时任务" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { API_BASE } from '../config'

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

const loading = ref(false)
const error = ref('')
const config = ref<Record<string, any> | null>(null)
const modelInfo = ref<Record<string, any> | null>(null)
const skills = ref<ResourceItem[]>([])
const tools = ref<ResourceItem[]>([])
const guardrails = ref<ResourceItem[]>([])
const approvalEvents = ref<ApprovalEvent[]>([])
const plugins = ref<ResourceItem[]>([])
const cronJobs = ref<ResourceItem[]>([])
const resolvingId = ref('')

const modelName = computed(() => modelInfo.value?.model || modelInfo.value?.name || modelInfo.value?.current_model || '未确认')
const modelProvider = computed(() => modelInfo.value?.provider || modelInfo.value?.vendor || modelInfo.value?.platform || '模型服务')

const configEntries = computed(() => toEntries(config.value, 8))
const modelEntries = computed(() => toEntries(modelInfo.value, 8))

async function load() {
  loading.value = true
  error.value = ''
  const [configData, modelData, skillsData, toolsData, guardrailsData, cronData, pluginsData] = await Promise.all([
    fetchOptional<Record<string, any>>('/api/config'),
    fetchOptional<Record<string, any>>('/api/model/info'),
    fetchOptional<Record<string, any>>('/api/skills'),
    fetchOptional<Record<string, any>>('/api/agent/tools'),
    fetchOptional<Record<string, any>>('/api/agent/guardrails'),
    fetchOptional<Record<string, any>>('/api/cron/jobs'),
    fetchOptional<Record<string, any>>('/api/plugins'),
  ])

  config.value = configData
  modelInfo.value = modelData
  skills.value = normalizeCollection(skillsData, ['skills'])
  tools.value = normalizeCollection(toolsData, ['tools'])
  guardrails.value = normalizeCollection(guardrailsData, ['tool_policies'])
  approvalEvents.value = normalizeCollection(guardrailsData, ['approval_events']) as ApprovalEvent[]
  cronJobs.value = normalizeCollection(cronData, ['jobs', 'cron_jobs'])
  plugins.value = normalizeCollection(pluginsData, ['plugins'])
  if (!configData && !modelData && skills.value.length === 0 && tools.value.length === 0 && guardrails.value.length === 0 && plugins.value.length === 0 && cronJobs.value.length === 0) {
    error.value = '暂时无法读取 Hermès 配置信息，请确认 Bridge 与 Hermès API 可达。'
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
            h('span', item.description || item.schedule || item.decision || item.risk || item.status || (item.enabled === false ? 'disabled' : 'enabled')),
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

.approval-item {
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

.approval-main strong {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
}

.approval-main span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 800;
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
  .resource-grid {
    grid-template-columns: 1fr;
  }
}
</style>
