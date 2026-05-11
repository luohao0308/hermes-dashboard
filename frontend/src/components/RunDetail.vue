<template>
  <section class="run-detail">
    <div class="detail-header">
      <button class="back-btn" @click="emit('back')">
        <ArrowLeft :size="16" />
        {{ t('common.back') }}
      </button>
      <div class="title-block">
        <div class="title-row">
          <h2>{{ run?.title || t('common.loading') }}</h2>
          <span v-if="run" :class="['status-badge', statusTone(run.status)]">{{ run.status }}</span>
        </div>
        <span class="run-id">{{ runId }}</span>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        <RefreshCcw :size="15" :class="{ spinning: loading }" />
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

    <div class="detail-grid">
      <div class="trace-workbench">
        <div class="workbench-header">
          <div>
            <h3>{{ t('runDetail.traceTimeline') }}</h3>
            <p>{{ spans.length }} spans captured for this workflow run.</p>
          </div>
          <div class="workbench-actions">
            <button v-if="run" class="ghost-action" @click="emit('exportRca')">
              <Download :size="14" />
              {{ t('common.export') }}
            </button>
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

        <TraceTimeline :run="run" :spans="spans" />
      </div>

      <aside class="analysis-rail">
        <div class="analysis-panel">
          <div class="panel-header">
            <div>
              <h3>
                <ShieldAlert :size="16" />
                {{ t('runDetail.rcaAnalysis') }}
              </h3>
              <p v-if="rcaReport">
                {{ t('runAnalysis.confidence') }} {{ Math.round(rcaReport.confidence * 100) }}%
              </p>
              <p v-else>{{ t('runDetail.rcaFailed') }}</p>
            </div>
          </div>
          <div class="panel-actions">
            <button class="action-btn primary" :disabled="loadingRca" @click="emit('analyzeRca')">
              <span v-if="loadingRca" class="spinner"></span>
              {{ loadingRca ? t('common.processing') : t('runDetail.generateRca') }}
            </button>
            <button v-if="rcaReport" class="action-btn secondary" @click="emit('exportRca')">
              {{ t('common.export') }}
            </button>
          </div>

          <div v-if="rcaReport" class="rca-content">
            <div class="rca-root">{{ rcaReport.root_cause }}</div>
            <div class="rca-meta">
              <span class="rca-badge" :class="'severity-' + (rcaReport.low_confidence ? 'low' : 'high')">
                {{ rcaReport.category }}
              </span>
              <span v-if="rcaReport.low_confidence" class="rca-badge severity-low">Low confidence</span>
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

        <div class="analysis-panel">
          <div class="panel-header">
            <div>
              <h3>
                <ListChecks :size="16" />
                {{ t('runDetail.runbook') }}
              </h3>
              <p v-if="runbook">{{ runbook.summary }}</p>
              <p v-else>{{ t('runDetail.runbookFailed') }}</p>
            </div>
          </div>
          <div class="panel-actions">
            <button class="action-btn primary" :disabled="loadingRunbook" @click="emit('generateRunbook')">
              <span v-if="loadingRunbook" class="spinner"></span>
              {{ loadingRunbook ? t('common.processing') : t('runDetail.generateRunbook') }}
            </button>
            <button v-if="runbook" class="action-btn secondary" @click="emit('exportRunbook')">
              {{ t('common.export') }}
            </button>
          </div>

          <div v-if="runbook" class="runbook-content">
            <div class="runbook-meta">
              <span class="rca-badge" :class="'severity-' + runbook.severity">{{ runbook.severity }}</span>
              <span>{{ t('runAnalysis.evidence') }}: {{ runbook.evidence_count }}</span>
            </div>
            <ol v-if="runbook.checklist?.length" class="checklist">
              <li v-for="(item, i) in runbook.checklist" :key="i">{{ item }}</li>
            </ol>
            <div v-if="runbook.markdown" class="runbook-markdown">
              <h4>Markdown</h4>
              <pre>{{ runbook.markdown }}</pre>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Download, ListChecks, RefreshCcw, ShieldAlert } from 'lucide-vue-next'
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
  const total = props.run.total_tokens ?? 0
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

function statusTone(status: string): string {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'running'
  if (status === 'error' || status === 'failed') return 'failed'
  return 'queued'
}
</script>

<style scoped>
.run-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-header,
.summary-card,
.trace-workbench,
.analysis-panel {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 22px;
}

.title-block {
  flex: 1;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 20px;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.run-id {
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.back-btn,
.refresh-btn,
.ghost-action,
.action-btn {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.back-btn,
.refresh-btn,
.ghost-action,
.action-btn {
  padding: 0 12px;
}

.refresh-btn:disabled,
.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.status-badge {
  padding: 4px 8px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.status-badge.success {
  color: #047857;
  background: #ecfdf5;
  border-color: #bbf7d0;
}

.status-badge.running {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.status-badge.failed {
  color: #be123c;
  background: #fff1f2;
  border-color: #fecdd3;
}

.status-badge.queued {
  color: #64748b;
  background: #f8fafc;
  border-color: #e2e8f0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.summary-card {
  min-height: 100px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 18px 20px;
}

.summary-card span {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-card strong {
  color: #0f172a;
  font-size: 24px;
  font-weight: 900;
}

.summary-card small {
  color: #64748b;
  font-size: 12px;
}

.status-completed { color: var(--success-color); }
.status-running { color: var(--accent-color); }
.status-error { color: var(--error-color); }
.status-queued { color: #64748b; }

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 18px;
  align-items: start;
}

.trace-workbench {
  overflow: hidden;
}

.workbench-header,
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: #f8fafc;
}

.workbench-header h3,
.panel-header h3 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.workbench-header p,
.panel-header p {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
}

.summary-panel {
  margin: 18px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: #ffffff;
}

.summary-section + .summary-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.panel-title {
  margin-bottom: 5px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-section p {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.65;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.summary-section.error p {
  color: #be123c;
}

.analysis-rail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.analysis-panel {
  overflow: hidden;
}

.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
}

.action-btn.primary {
  color: #ffffff;
  background: var(--accent-color);
  border-color: var(--accent-color);
}

.rca-content,
.runbook-content {
  padding: 16px 18px 18px;
}

.rca-root {
  margin-bottom: 12px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.55;
}

.rca-meta,
.runbook-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.rca-badge {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.severity-high {
  color: #be123c;
  background: #fff1f2;
}

.severity-medium {
  color: #b45309;
  background: #fffbeb;
}

.severity-low {
  color: #64748b;
  background: #f8fafc;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.evidence-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #f8fafc;
}

.ev-source {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.ev-title {
  color: #0f172a;
  font-size: 12px;
  font-weight: 800;
}

.ev-detail {
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.next-actions h4,
.runbook-markdown h4 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 900;
}

.next-actions ul,
.checklist {
  margin: 0;
  padding-left: 20px;
  color: #475569;
  font-size: 12px;
  line-height: 1.8;
}

.runbook-markdown pre {
  max-height: 260px;
  margin: 12px 0 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 11px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.error-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid #fecdd3;
  border-radius: 12px;
  background: #fff1f2;
  color: #be123c;
  font-size: 13px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .detail-header,
  .workbench-header,
  .panel-header {
    align-items: stretch;
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
