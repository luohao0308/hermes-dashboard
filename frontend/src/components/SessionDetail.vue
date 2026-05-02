<template>
  <section class="session-detail">
    <div class="detail-header">
      <button class="back-btn" @click="emit('back')">{{ t('common.back') }}</button>
      <div class="title-block">
        <span class="eyebrow">{{ t('session.title') }}</span>
        <h2>{{ title }}</h2>
        <span class="session-id">#{{ taskId }}</span>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? t('common.loading') : t('common.refresh') }}
      </button>
      <button class="refresh-btn" @click="emit('open-chat')">{{ t('session.continueChat') }}</button>
    </div>

    <div v-if="error" class="error-box">
      <strong>{{ t('session.loadFailed') }}</strong>
      <span>{{ error }}</span>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <span>{{ t('session.status') }}</span>
        <strong>{{ statusText }}</strong>
        <small>{{ diagnosis }}</small>
      </div>
      <div class="summary-card">
        <span>{{ t('session.messageCount') }}</span>
        <strong>{{ messageCount }}</strong>
        <small>{{ modelText }}</small>
      </div>
      <div class="summary-card">
        <span>{{ t('session.duration') }}</span>
        <strong>{{ formatDuration(duration) }}</strong>
        <small>{{ timeRange }}</small>
      </div>
      <div class="summary-card">
        <span>{{ t('session.token') }}</span>
        <strong>{{ formatNumber(tokenTotal) }}</strong>
        <small>{{ inputTokens }} in / {{ outputTokens }} out</small>
      </div>
    </div>

    <div class="analysis-row">
      <div class="analysis-panel">
        <div class="panel-title">{{ t('session.reviewDiagnosis') }}</div>
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
        <div class="panel-title">{{ t('session.relatedLogs') }}</div>
        <div v-if="relatedLogs.length > 0" class="related-logs">
          <div v-for="(log, idx) in relatedLogs" :key="idx" class="related-log" :class="log.type">
            <span>{{ log.type }}</span>
            <p>{{ log.message }}</p>
          </div>
        </div>
        <div v-else class="empty-block">{{ t('session.noMatchingLogs') }}</div>
      </div>
    </div>

    <div class="rca-panel">
      <div class="rca-header">
        <div>
          <div class="panel-title">{{ t('session.rcaAnalysis') }}</div>
          <p>{{ rcaSubtitle }}</p>
        </div>
        <div class="rca-actions">
          <button v-if="rcaReport" class="secondary-btn" @click="copyRcaReport">{{ t('session.copyRca') }}</button>
          <button class="primary-btn" :disabled="rcaLoading" @click="emit('analyze-rca')">
            <span v-if="rcaLoading" class="spinner"></span>
            {{ rcaLoading ? t('session.analyzing') : t('session.analyzeFailure') }}
          </button>
        </div>
      </div>

      <div v-if="rcaReport" class="rca-result" :class="{ cautious: rcaReport.low_confidence }">
        <div class="rca-cause">
          <span>{{ categoryLabel(rcaReport.category) }}</span>
          <strong>{{ rcaReport.root_cause }}</strong>
          <small>{{ t('session.confidence') }} {{ rcaConfidenceText }}</small>
        </div>
        <div class="rca-columns">
          <div>
            <h4>{{ t('session.evidenceChain') }}</h4>
            <article v-for="(item, idx) in rcaReport.evidence" :key="idx" class="evidence-item" :class="item.severity">
              <span>{{ item.source }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
            </article>
          </div>
          <div>
            <h4>{{ t('session.nextActions') }}</h4>
            <ol class="action-list">
              <li v-for="action in rcaReport.next_actions" :key="action">{{ action }}</li>
            </ol>
          </div>
        </div>
      </div>
      <div v-else class="empty-block">{{ t('session.noRca') }}</div>
    </div>

    <div class="runbook-panel">
      <div class="rca-header">
        <div>
          <div class="panel-title">{{ t('session.runbook') }}</div>
          <p>{{ runbookSubtitle }}</p>
        </div>
        <div class="rca-actions">
          <button v-if="runbookReport" class="secondary-btn" @click="copyRunbook">{{ t('session.copyRunbook') }}</button>
          <button v-if="runbookReport" class="secondary-btn" :disabled="exportLoading" @click="emit('export-markdown')">
            {{ exportLoading ? t('session.exporting') : t('session.exportMarkdown') }}
          </button>
          <button class="primary-btn" :disabled="runbookLoading" @click="emit('generate-runbook')">
            <span v-if="runbookLoading" class="spinner"></span>
            {{ runbookLoading ? t('session.generating') : t('session.generateRunbook') }}
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
        <div class="runbook-steps">
          <div v-for="(step, idx) in runbookSteps" :key="step.step_id" class="runbook-step">
            <span>{{ idx + 1 }}</span>
            <p>{{ step.label }}</p>
            <button
              v-if="step.requires_confirmation"
              class="confirm-step-btn"
              :disabled="['completed', 'blocked_unsafe'].includes(step.status)"
              @click="step.status === 'confirmed' ? emit('execute-runbook-step', step.step_id) : emit('confirm-runbook-step', step.step_id)"
            >
              {{ stepButtonLabel(step) }}
            </button>
          </div>
        </div>
      </div>
      <div v-else class="empty-block">{{ t('session.noRunbook') }}</div>
    </div>

    <TraceTimeline :run="traceRun" :spans="traceSpans" />

    <div class="timeline-panel">
      <div class="panel-title">{{ t('session.messageTimeline') }}</div>
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
      <div v-else class="empty-block">{{ t('session.noMessages') }}</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import TraceTimeline from './TraceTimeline.vue'
import type { HistoryItem, LogItem, SessionDetailData, TraceRun, TraceSpan, RcaReport, RunbookReport, RunbookStep } from '../types'
import { useI18n } from "vue-i18n"
import { formatDate, formatDuration, formatNumber } from '../composables/useFormatters'

const { t } = useI18n()
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
  'confirm-runbook-step': [stepId: string]
  'execute-runbook-step': [stepId: string]
  'export-markdown': []
  'open-chat': []
}>()

const title = computed(() => props.detail?.name || props.item?.name || `Session ${props.taskId.slice(0, 8)}`)
const status = computed(() => props.detail?.status || props.item?.status || 'completed')
const statusText = computed(() => {
  const map: Record<string, string> = {
    running: t('common.running'),
    completed: t('common.success'),
    success: t('common.success'),
    failed: t('common.error'),
    cancelled: t('common.disabled'),
  }
  return map[status.value] || status.value
})

const messageCount = computed(() =>
  props.detail?.message_count ?? props.detail?.messages?.length ?? props.item?.message_count ?? 0
)
const modelText = computed(() => props.detail?.model || props.item?.model || t('session.modelUnconfirmed'))
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
  if (status.value === 'running') return t('session.taskRunning')
  if (props.detail?.end_reason && props.detail.end_reason !== 'completed') return t('session.endReason') + '：' + props.detail.end_reason
  if (hasErrorSignal.value) return t('session.errorSignal')
  if (messageCount.value === 0) return t('session.noMessages_')
  return t('session.noFailure')
})

const diagnosisHint = computed(() => {
  if (status.value === 'running') return t('session.runningHint')
  if (hasErrorSignal.value) return t('session.errorHint')
  if (messageCount.value === 0) return t('session.noMessageHint')
  return t('session.normalHint')
})

const signals = computed(() => {
  const result = []
  if (modelText.value !== t('session.modelUnconfirmed')) result.push(t('trace.model') + '：' + modelText.value)
  if (messageCount.value > 0) result.push(messageCount.value + ' ' + t('session.messages'))
  if (tokenTotal.value > 0) result.push(`${formatNumber(tokenTotal.value)} tokens`)
  if (relatedLogs.value.length > 0) result.push(`${relatedLogs.value.length} ${t('session.relatedLogs_')}`)
  if (props.detail?.end_reason) result.push(`end_reason=${props.detail.end_reason}`)
  return result.length > 0 ? result : [t('session.noExtraSignals')]
})

const rcaConfidenceText = computed(() => {
  if (!props.rcaReport) return '0%'
  return `${Math.round(props.rcaReport.confidence * 100)}%`
})

const rcaSubtitle = computed(() => {
  if (props.rcaLoading) return t('session.rcaAggregating')
  if (props.rcaReport?.low_confidence) return t('session.rcaLowConfidence')
  if (props.rcaReport) return t('session.rcaGenerated', { analyzer: props.rcaReport.analyzer })
  return t('session.rcaDefault')
})

const runbookSubtitle = computed(() => {
  if (props.runbookLoading) return t('session.runbookAggregating')
  if (props.runbookReport) return t('session.runbookTodos', { severity: props.runbookReport.severity, count: props.runbookReport.checklist.length })
  return t('session.runbookDefault')
})

const runbookSteps = computed<RunbookStep[]>(() => {
  if (!props.runbookReport) return []
  if (props.runbookReport.execution_steps?.length) return props.runbookReport.execution_steps
  return props.runbookReport.checklist.map((label, idx) => ({
    step_id: `step-${idx + 1}`,
    label,
    action_type: 'manual_check',
    requires_confirmation: false,
    status: 'pending',
  }))
})

function stepButtonLabel(step: RunbookStep): string {
  if (step.status === 'confirmed') return t('session.stepExecute')
  if (step.status === 'completed') return t('session.stepCompleted')
  if (step.status === 'blocked_unsafe') return t('session.stepBlocked')
  return t('session.stepConfirm')
}

const timeRange = computed(() => {
  const start = props.detail?.started_at
  const end = props.detail?.completed_at || props.item?.completed_at
  if (!start && !end) return t('session.timeUnconfirmed')
  if (!start) return t('session.completedAt', { date: formatDate(end) })
  if (!end) return t('session.startedAt', { date: formatDate(start) })
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
    user: t('session.roleUser'),
    assistant: t('session.roleAssistant'),
    system: t('session.roleSystem'),
    tool: t('session.roleTool'),
  }
  return map[role] || role
}

function categoryLabel(category: string): string {
  const map: Record<string, string> = {
    tool: t('session.roleTool'),
    network: t('session.catNetwork'),
    model: t('session.catModel'),
    config: t('session.catConfig'),
    data: t('session.catData'),
    unknown: t('session.catUnknown'),
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

.runbook-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.runbook-step {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  gap: 10px;
  align-items: start;
}

.runbook-step span {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent-color);
  font-size: 11px;
  font-weight: 900;
}

.runbook-step p {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.confirm-step-btn {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--warning-color);
  border-radius: var(--radius-md);
  background: var(--warning-soft);
  color: var(--warning-color);
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.confirm-step-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
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
