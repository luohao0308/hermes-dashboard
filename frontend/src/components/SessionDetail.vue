<template>
  <section class="session-detail">
    <div class="detail-header">
      <button class="back-btn" @click="emit('back')">返回</button>
      <div class="title-block">
        <span class="eyebrow">Session 复盘</span>
        <h2>{{ title }}</h2>
        <span class="session-id">#{{ taskId }}</span>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '加载中' : '刷新' }}
      </button>
    </div>

    <div v-if="error" class="error-box">
      <strong>详情加载失败</strong>
      <span>{{ error }}</span>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <span>状态</span>
        <strong>{{ statusText }}</strong>
        <small>{{ diagnosis }}</small>
      </div>
      <div class="summary-card">
        <span>消息数</span>
        <strong>{{ messageCount }}</strong>
        <small>{{ modelText }}</small>
      </div>
      <div class="summary-card">
        <span>耗时</span>
        <strong>{{ formatDuration(duration) }}</strong>
        <small>{{ timeRange }}</small>
      </div>
      <div class="summary-card">
        <span>Token</span>
        <strong>{{ formatNumber(tokenTotal) }}</strong>
        <small>{{ inputTokens }} in / {{ outputTokens }} out</small>
      </div>
    </div>

    <div class="analysis-row">
      <div class="analysis-panel">
        <div class="panel-title">复盘判断</div>
        <div class="diagnosis-card" :class="diagnosisTone">
          <span class="diagnosis-dot"></span>
          <div>
            <strong>{{ diagnosis }}</strong>
            <p>{{ diagnosisHint }}</p>
          </div>
        </div>
        <div class="signal-stack">
          <div v-for="signal in signals" :key="signal" class="signal-chip">{{ signal }}</div>
        </div>
      </div>

      <div class="analysis-panel">
        <div class="panel-title">关联日志</div>
        <div v-if="relatedLogs.length > 0" class="related-logs">
          <div v-for="(log, idx) in relatedLogs" :key="idx" class="related-log" :class="log.type">
            <span>{{ log.type }}</span>
            <p>{{ log.message }}</p>
          </div>
        </div>
        <div v-else class="empty-block">当前抓取的日志中没有匹配到该 session</div>
      </div>
    </div>

    <TraceTimeline :run="traceRun" :spans="traceSpans" />

    <div class="timeline-panel">
      <div class="panel-title">消息时间线</div>
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 4" :key="i" class="skeleton-row"></div>
      </div>
      <div v-else-if="normalizedMessages.length > 0" class="timeline">
        <article v-for="(message, idx) in normalizedMessages" :key="idx" class="timeline-item" :class="message.role">
          <div class="timeline-marker"></div>
          <div class="timeline-content">
            <div class="message-meta">
              <strong>{{ roleLabel(message.role) }}</strong>
              <span>{{ formatDate(message.timestamp) }}</span>
            </div>
            <p>{{ message.content }}</p>
          </div>
        </article>
      </div>
      <div v-else class="empty-block">暂无消息记录</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import TraceTimeline from './TraceTimeline.vue'

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

interface LogItem {
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error' | 'debug'
}

interface MessageItem {
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
  messages?: MessageItem[]
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

const props = defineProps<{
  taskId: string
  item: HistoryItem | null
  detail: SessionDetailData | null
  logs: LogItem[]
  traceRun: TraceRun | null
  traceSpans: TraceSpan[]
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  back: []
  refresh: []
}>()

const title = computed(() => props.detail?.name || props.item?.name || `Session ${props.taskId.slice(0, 8)}`)
const status = computed(() => props.detail?.status || props.item?.status || 'completed')
const statusText = computed(() => {
  const map: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status.value] || status.value
})

const messageCount = computed(() =>
  props.detail?.message_count ?? props.detail?.messages?.length ?? props.item?.message_count ?? 0
)
const modelText = computed(() => props.detail?.model || props.item?.model || '模型未确认')
const duration = computed(() => props.detail?.duration ?? props.item?.duration ?? 0)
const inputTokens = computed(() => props.detail?.input_tokens ?? props.item?.input_tokens ?? 0)
const outputTokens = computed(() => props.detail?.output_tokens ?? props.item?.output_tokens ?? 0)
const tokenTotal = computed(() => inputTokens.value + outputTokens.value)

const normalizedMessages = computed(() => {
  return (props.detail?.messages || []).map(message => ({
    role: normalizeRole(message.role),
    content: String(message.content || message.text || message.message || '').trim(),
    timestamp: message.timestamp || message.created_at || '',
  })).filter(message => message.content)
})

const relatedLogs = computed(() => {
  const needle = props.taskId.toLowerCase()
  return props.logs
    .filter(log => log.message.toLowerCase().includes(needle) || log.message.toLowerCase().includes(needle.slice(0, 8)))
    .slice(0, 6)
})

const diagnosisTone = computed(() => {
  if (status.value === 'running') return 'warn'
  if (status.value === 'failed' || props.detail?.end_reason === 'error' || hasErrorSignal.value) return 'bad'
  return 'good'
})

const hasErrorSignal = computed(() =>
  relatedLogs.value.some(log => log.type === 'error') ||
  normalizedMessages.value.some(message => /error|failed|exception|traceback|失败|错误/i.test(message.content))
)

const diagnosis = computed(() => {
  if (status.value === 'running') return '任务仍在运行'
  if (props.detail?.end_reason && props.detail.end_reason !== 'completed') return `结束原因：${props.detail.end_reason}`
  if (hasErrorSignal.value) return '发现错误信号'
  if (messageCount.value === 0) return '缺少消息记录'
  return '未发现明显失败信号'
})

const diagnosisHint = computed(() => {
  if (status.value === 'running') return '建议观察最近输出时间，必要时打开终端或日志确认是否卡住。'
  if (hasErrorSignal.value) return '建议优先查看关联日志和最后几条消息，确认失败发生在模型、工具还是网络层。'
  if (messageCount.value === 0) return 'Hermès 没有返回消息，可能是刚启动、会话被清理，或 API 未返回明细。'
  return '该 session 看起来正常，可以继续查看消息时间线做人工复盘。'
})

const signals = computed(() => {
  const result = []
  if (modelText.value !== '模型未确认') result.push(`模型：${modelText.value}`)
  if (messageCount.value > 0) result.push(`${messageCount.value} 条消息`)
  if (tokenTotal.value > 0) result.push(`${formatNumber(tokenTotal.value)} tokens`)
  if (relatedLogs.value.length > 0) result.push(`${relatedLogs.value.length} 条关联日志`)
  if (props.detail?.end_reason) result.push(`end_reason=${props.detail.end_reason}`)
  return result.length > 0 ? result : ['暂无额外信号']
})

const timeRange = computed(() => {
  const start = props.detail?.started_at
  const end = props.detail?.completed_at || props.item?.completed_at
  if (!start && !end) return '时间未确认'
  if (!start) return `完成 ${formatDate(end)}`
  if (!end) return `开始 ${formatDate(start)}`
  return `${formatDate(start)} - ${formatDate(end)}`
})

function normalizeRole(role?: string): string {
  const value = (role || 'assistant').toLowerCase()
  if (value.includes('user')) return 'user'
  if (value.includes('system')) return 'system'
  if (value.includes('tool')) return 'tool'
  return 'assistant'
}

function roleLabel(role: string): string {
  const map: Record<string, string> = {
    user: '用户',
    assistant: 'Agent',
    system: '系统',
    tool: '工具',
  }
  return map[role] || role
}

function formatDate(timestamp?: string): string {
  if (!timestamp) return '时间未知'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0s'
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins < 60) return `${mins}m ${secs}s`
  const hours = Math.floor(mins / 60)
  return `${hours}h ${mins % 60}m`
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
  return String(value)
}
</script>

<style scoped>
.session-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-header,
.summary-card,
.analysis-panel,
.timeline-panel,
.error-box {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 24px;
}

.title-block {
  flex: 1;
  min-width: 0;
}

.eyebrow {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.title-block h2 {
  margin: 2px 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.session-id {
  color: var(--text-secondary);
  font-size: 12px;
}

.back-btn,
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 112px;
  padding: 18px 20px;
}

.summary-card span,
.panel-title {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.summary-card strong {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 800;
}

.summary-card small {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.analysis-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.analysis-panel,
.timeline-panel {
  padding: 20px 24px;
}

.panel-title {
  margin-bottom: 14px;
}

.diagnosis-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--success-soft);
}

.diagnosis-card.warn {
  background: var(--warning-soft);
}

.diagnosis-card.bad {
  background: var(--error-soft);
}

.diagnosis-dot {
  width: 9px;
  height: 9px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--success-color);
}

.diagnosis-card.warn .diagnosis-dot {
  background: var(--warning-color);
}

.diagnosis-card.bad .diagnosis-dot {
  background: var(--error-color);
}

.diagnosis-card strong {
  color: var(--text-primary);
  font-size: 14px;
}

.diagnosis-card p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.signal-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.signal-chip {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 12px;
}

.related-logs {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.related-log {
  display: grid;
  grid-template-columns: 68px 1fr;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.related-log span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.related-log p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.related-log.error {
  border-color: rgba(239, 68, 68, 0.25);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 12px;
}

.timeline-marker {
  width: 10px;
  height: 10px;
  margin-top: 8px;
  border-radius: 50%;
  background: var(--accent-color);
}

.timeline-item.user .timeline-marker {
  background: var(--success-color);
}

.timeline-item.system .timeline-marker,
.timeline-item.tool .timeline-marker {
  background: var(--warning-color);
}

.timeline-content {
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.message-meta strong {
  color: var(--text-primary);
  font-size: 13px;
}

.message-meta span {
  color: var(--text-muted);
  font-size: 12px;
}

.timeline-content p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.empty-block,
.error-box {
  padding: 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.error-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
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

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-row {
  height: 74px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-secondary) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .summary-grid,
  .analysis-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .detail-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid,
  .analysis-row {
    grid-template-columns: 1fr;
  }

  .back-btn,
  .refresh-btn {
    width: 100%;
  }
}
</style>
