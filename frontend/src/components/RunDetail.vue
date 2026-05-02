<template>
  <section class="run-detail">
    <div class="detail-header">
      <button class="back-btn" @click="emit('back')">{{ t('common.back') }}</button>
      <div class="title-block">
        <span class="eyebrow">{{ t('runs.title') }}</span>
        <h2>{{ run?.title || t('common.loading') }}</h2>
        <span class="run-id">{{ runId }}</span>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? t('common.loading') : t('common.refresh') }}
      </button>
    </div>

    <div v-if="error" class="error-box">
      <strong>{{ t('runs.failedToLoad') }}</strong>
      <span>{{ error }}</span>
    </div>

    <div v-if="run" class="summary-grid">
      <div class="summary-card">
        <span>{{ t('common.status') }}</span>
        <strong :class="'status-' + run.status">{{ run.status }}</strong>
      </div>
      <div class="summary-card">
        <span>{{ t('runs.duration') }}</span>
        <strong>{{ durationText }}</strong>
        <small>{{ timeRange }}</small>
      </div>
      <div class="summary-card">
        <span>{{ t('runs.tokens') }}</span>
        <strong>{{ tokenText }}</strong>
      </div>
      <div class="summary-card">
        <span>{{ t('runs.cost') }}</span>
        <strong>{{ costText }}</strong>
      </div>
    </div>

    <div v-if="run?.input_summary || run?.output_summary || run?.error_summary" class="summary-panel">
      <div v-if="run.input_summary" class="summary-section">
        <div class="panel-title">Input</div>
        <p>{{ run.input_summary }}</p>
      </div>
      <div v-if="run.output_summary" class="summary-section">
        <div class="panel-title">Output</div>
        <p>{{ run.output_summary }}</p>
      </div>
      <div v-if="run.error_summary" class="summary-section error">
        <div class="panel-title">Error</div>
        <p>{{ run.error_summary }}</p>
      </div>
    </div>

    <!-- RCA Section -->
    <div class="analysis-panel">
      <div class="panel-header">
        <div>
          <h3>{{ t('runDetail.rcaAnalysis') }}</h3>
          <p v-if="rcaReport">
            {{ rcaReport.root_cause }} — {{ t('runAnalysis.confidence') }} {{ Math.round(rcaReport.confidence * 100) }}%
          </p>
          <p v-else>{{ t('runDetail.rcaFailed') }}</p>
        </div>
        <div class="panel-actions">
          <button class="action-btn" :disabled="loadingRca" @click="emit('analyzeRca')">
            <span v-if="loadingRca" class="spinner"></span>
            {{ loadingRca ? t('common.processing') : t('runDetail.generateRca') }}
          </button>
          <button v-if="rcaReport" class="action-btn secondary" @click="emit('exportRca')">
            {{ t('common.export') }}
          </button>
        </div>
      </div>

      <div v-if="rcaReport" class="rca-content">
        <div class="rca-meta">
          <span class="rca-badge" :class="'severity-' + (rcaReport.low_confidence ? 'low' : 'high')">
            {{ rcaReport.category }}
          </span>
          <span v-if="rcaReport.low_confidence" class="rca-badge severity-low">{{ t('runAnalysis.confidence') }}</span>
        </div>

        <div v-if="rcaReport.evidence?.length" class="evidence-list">
          <div v-for="(ev, i) in rcaReport.evidence" :key="i" class="evidence-item" :class="'severity-' + ev.severity">
            <span class="ev-source">{{ ev.source }}</span>
            <span class="ev-title">{{ ev.title }}</span>
            <span class="ev-detail">{{ ev.detail }}</span>
          </div>
        </div>

        <div v-if="rcaReport.next_actions?.length" class="next-actions">
          <h4>{{ t('runAnalysis.steps') }}</h4>
          <ul>
            <li v-for="(action, i) in rcaReport.next_actions" :key="i">{{ action }}</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Runbook Section -->
    <div class="analysis-panel">
      <div class="panel-header">
        <div>
          <h3>{{ t('runDetail.runbook') }}</h3>
          <p v-if="runbook">{{ runbook.summary }}</p>
          <p v-else>{{ t('runDetail.runbookFailed') }}</p>
        </div>
        <div class="panel-actions">
          <button class="action-btn" :disabled="loadingRunbook" @click="emit('generateRunbook')">
            <span v-if="loadingRunbook" class="spinner"></span>
            {{ loadingRunbook ? t('common.processing') : t('runDetail.generateRunbook') }}
          </button>
          <button v-if="runbook" class="action-btn secondary" @click="emit('exportRunbook')">
            {{ t('common.export') }}
          </button>
        </div>
      </div>

      <div v-if="runbook" class="runbook-content">
        <div class="runbook-meta">
          <span class="rca-badge" :class="'severity-' + runbook.severity">
            {{ runbook.severity }}
          </span>
          <span class="runbook-evidence">{{ t('runAnalysis.evidence') }}: {{ runbook.evidence_count }}</span>
        </div>

        <div v-if="runbook.checklist?.length" class="checklist">
          <h4>{{ t('runAnalysis.steps') }}</h4>
          <ul>
            <li v-for="(item, i) in runbook.checklist" :key="i">{{ item }}</li>
          </ul>
        </div>

        <div v-if="runbook.markdown" class="runbook-markdown">
          <h4>Markdown</h4>
          <pre>{{ runbook.markdown }}</pre>
        </div>
      </div>
    </div>

    <TraceTimeline :run="run" :spans="spans" />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import TraceTimeline from './TraceTimeline.vue'
import type { RcaReport, RunbookReport, WorkflowRun, WorkflowSpan } from '../types'
import { formatDate, formatDuration, formatNumber } from '../composables/useFormatters'

const { t } = useI18n()

const props = defineProps<{
  runId: string
  run: WorkflowRun | null
  spans: WorkflowSpan[]
  loading?: boolean
  error?: string | null
  rcaReport?: RcaReport | null
  runbook?: RunbookReport | null
  loadingRca?: boolean
  loadingRunbook?: boolean
}>()

const emit = defineEmits<{
  back: []
  refresh: []
  analyzeRca: []
  generateRunbook: []
  exportRca: []
  exportRunbook: []
}>()

const durationText = computed(() => {
  if (!props.run?.duration_ms) return '--'
  return formatDuration(props.run.duration_ms)
})

const tokenText = computed(() => {
  if (!props.run) return '--'
  const total = (props.run.total_tokens ?? 0)
  return total > 0 ? formatNumber(total) : '--'
})

const costText = computed(() => {
  if (!props.run?.total_cost) return '--'
  return `$${props.run.total_cost.toFixed(4)}`
})

const timeRange = computed(() => {
  if (!props.run) return ''
  const start = props.run.started_at
  const end = props.run.ended_at
  if (!start) return ''
  if (!end) return `Started ${formatDate(start)}`
  return `${formatDate(start)} - ${formatDate(end)}`
})
</script>

<style scoped>
.run-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
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

.run-id {
  color: var(--text-secondary);
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
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
  min-height: 100px;
  padding: 18px 20px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.summary-card span {
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
}

.status-completed { color: var(--success-color); }
.status-running { color: var(--warning-color); }
.status-error { color: var(--error-color); }
.status-queued { color: var(--text-muted); }

.summary-panel {
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.summary-section + .summary-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.panel-title {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.summary-section p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.summary-section.error p {
  color: var(--error-color);
}

.error-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  background: var(--error-soft);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  font-size: 13px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.analysis-panel {
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 800;
}

.panel-header p {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--accent-color);
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent-color);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.secondary {
  border-color: var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.rca-content,
.runbook-content {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.rca-meta,
.runbook-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.rca-badge {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 700;
}

.severity-high {
  background: var(--error-soft);
  color: var(--error-color);
}

.severity-medium {
  background: var(--warning-soft);
  color: var(--warning-color);
}

.severity-low {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.evidence-item {
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ev-source {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.ev-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.ev-detail {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.next-actions h4,
.checklist h4,
.runbook-markdown h4 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.next-actions ul,
.checklist ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.8;
}

.runbook-evidence {
  font-size: 11px;
  color: var(--text-muted);
}

.runbook-markdown pre {
  margin: 0;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 300px;
  overflow-y: auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .detail-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .back-btn,
  .refresh-btn {
    width: 100%;
  }
}
</style>
