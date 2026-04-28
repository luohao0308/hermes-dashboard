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
      <button class="refresh-btn" @click="emit('open-chat')">继续对话</button>
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

    <div class="rca-panel">
      <div class="rca-header">
        <div>
          <div class="panel-title">AI 失败原因分析</div>
          <p>{{ rcaSubtitle }}</p>
        </div>
        <div class="rca-actions">
          <button v-if="rcaReport" class="secondary-btn" @click="copyRcaReport">复制复盘</button>
          <button class="primary-btn" :disabled="rcaLoading" @click="emit('analyze-rca')">
            <span v-if="rcaLoading" class="spinner"></span>
            {{ rcaLoading ? '分析中' : '一键分析失败原因' }}
          </button>
        </div>
      </div>

      <div v-if="rcaReport" class="rca-result" :class="{ cautious: rcaReport.low_confidence }">
        <div class="rca-cause">
          <span>{{ categoryLabel(rcaReport.category) }}</span>
          <strong>{{ rcaReport.root_cause }}</strong>
          <small>置信度 {{ rcaConfidenceText }}</small>
        </div>
        <div class="rca-columns">
          <div>
            <h4>证据链</h4>
            <article v-for="(item, idx) in rcaReport.evidence" :key="idx" class="evidence-item" :class="item.severity">
              <span>{{ item.source }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
            </article>
          </div>
          <div>
            <h4>下一步动作</h4>
            <ol class="action-list">
              <li v-for="action in rcaReport.next_actions" :key="action">{{ action }}</li>
            </ol>
          </div>
        </div>
      </div>
      <div v-else class="empty-block">尚未生成 RCA，点击按钮后会聚合 session、日志和 trace 证据。</div>
    </div>

    <div class="runbook-panel">
      <div class="rca-header">
        <div>
          <div class="panel-title">Runbook 自动化</div>
          <p>{{ runbookSubtitle }}</p>
        </div>
        <div class="rca-actions">
          <button v-if="runbookReport" class="secondary-btn" @click="copyRunbook">复制 Runbook</button>
          <button v-if="runbookReport" class="secondary-btn" :disabled="exportLoading" @click="emit('export-markdown')">
            {{ exportLoading ? '导出中' : '导出 Markdown' }}
          </button>
          <button class="primary-btn" :disabled="runbookLoading" @click="emit('generate-runbook')">
            <span v-if="runbookLoading" class="spinner"></span>
            {{ runbookLoading ? '生成中' : '生成 Runbook' }}
          </button>
        </div>
      </div>
      <div v-if="runbookReport" class="runbook-result">
        <div class="rca-cause">
          <span>{{ runbookReport.severity }}</span>
          <strong>{{ runbookReport.title }}</strong>
          <small>{{ runbookReport.generator }}</small>
        </div>
        <pre>{{ runbookReport.markdown }}</pre>
      </div>
      <div v-else class="empty-block">尚未生成 Runbook，会基于 RCA、trace 和 session 摘要生成复盘清单。</div>
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

const props = defineProps<{
  taskId: string
  item: HistoryItem | null
  detail: SessionDetailData | null
  logs: LogItem[]
  traceRun: TraceRun | null
  traceSpans: TraceSpan[]
  rcaReport: RcaReport | null
  rcaLoading?: boolean
  runbookReport: RunbookReport | null
  runbookLoading?: boolean
  exportLoading?: boolean
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  back: []
  refresh: []
  'analyze-rca': []
  'generate-runbook': []
  'export-markdown': []
  'open-chat': []
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

const rcaConfidenceText = computed(() => {
  if (!props.rcaReport) return '0%'
  return `${Math.round(props.rcaReport.confidence * 100)}%`
})

const rcaSubtitle = computed(() => {
  if (props.rcaLoading) return '正在聚合 session、日志和 trace'
  if (props.rcaReport?.low_confidence) return '当前证据不足，建议人工核对原始 trace'
  if (props.rcaReport) return `由 ${props.rcaReport.analyzer} 生成`
  return '生成可复制的 root cause、证据链和后续动作'
})

const runbookSubtitle = computed(() => {
  if (props.runbookLoading) return '正在整理复盘摘要、证据和处理步骤'
  if (props.runbookReport) return `${props.runbookReport.severity} / ${props.runbookReport.checklist.length} 个待办`
  return '生成可复制到 issue、PR 或 Notion 的执行清单'
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

function categoryLabel(category: string): string {
  const map: Record<string, string> = {
    tool: '工具',
    network: '网络',
    model: '模型',
    config: '配置',
    data: '数据',
    unknown: '未知',
  }
  return map[category] || category
}

function copyRcaReport() {
  if (!props.rcaReport || typeof navigator === 'undefined' || !navigator.clipboard) return
  const report = props.rcaReport
  const evidence = report.evidence.map(item => `- [${item.source}] ${item.title}: ${item.detail}`).join('\n')
  const actions = report.next_actions.map((action, idx) => `${idx + 1}. ${action}`).join('\n')
  void navigator.clipboard.writeText([
    `Root cause: ${report.root_cause}`,
    `Category: ${report.category}`,
    `Confidence: ${Math.round(report.confidence * 100)}%`,
    '',
    'Evidence:',
    evidence,
    '',
    'Next actions:',
    actions,
  ].join('\n'))
}

function copyRunbook() {
  if (!props.runbookReport || typeof navigator === 'undefined' || !navigator.clipboard) return
  void navigator.clipboard.writeText(props.runbookReport.markdown)
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
.rca-panel,
.runbook-panel,
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
.rca-panel,
.runbook-panel,
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

.rca-header,
.rca-actions,
.rca-cause {
  display: flex;
  align-items: center;
}

.rca-header {
  justify-content: space-between;
  gap: 18px;
}

.rca-header p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.rca-actions {
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.primary-btn,
.secondary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.primary-btn {
  border: 1px solid var(--accent-color);
  background: var(--accent-color);
  color: white;
}

.primary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.secondary-btn {
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.rca-result {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid rgba(16, 185, 129, 0.28);
  border-radius: var(--radius-md);
  background: var(--success-soft);
}

.runbook-result {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.runbook-result pre {
  max-height: 360px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.rca-result.cautious {
  border-color: rgba(245, 158, 11, 0.32);
  background: var(--warning-soft);
}

.rca-cause {
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.rca-cause span {
  padding: 4px 9px;
  border-radius: var(--radius-pill);
  background: var(--bg-primary);
  color: var(--accent-color);
  font-size: 11px;
  font-weight: 800;
}

.rca-cause strong {
  color: var(--text-primary);
  font-size: 15px;
}

.rca-cause small {
  color: var(--text-secondary);
  font-size: 12px;
}

.rca-columns {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}

.rca-columns h4 {
  margin: 0 0 10px;
  color: var(--text-primary);
  font-size: 13px;
}

.evidence-item {
  margin-bottom: 10px;
  padding: 11px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.evidence-item.high {
  border-color: rgba(239, 68, 68, 0.28);
}

.evidence-item.medium {
  border-color: rgba(245, 158, 11, 0.28);
}

.evidence-item span {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.evidence-item strong {
  display: block;
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 12px;
}

.evidence-item p,
.action-list li {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.evidence-item p {
  margin: 4px 0 0;
}

.action-list {
  margin: 0;
  padding-left: 18px;
}

.action-list li + li {
  margin-top: 8px;
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
  .analysis-row,
  .rca-columns {
    grid-template-columns: 1fr;
  }

  .back-btn,
  .refresh-btn,
  .primary-btn,
  .secondary-btn {
    width: 100%;
  }

  .rca-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
