<template>
  <div class="eval-dashboard">
    <div class="panel-header">
      <div>
        <h2>{{ t('evals.title') }}</h2>
        <p class="subtitle">{{ t('evals.title') }}</p>
      </div>
      <div class="header-actions">
        <select v-model="selectedRuntime" class="filter-select" @change="loadSummary">
          <option value="">{{ t('common.all') }} {{ t('runs.runtime') }}</option>
          <option v-for="rt in runtimes" :key="rt.id" :value="rt.id">
            {{ rt.name }}
          </option>
        </select>
        <button class="refresh-btn" :disabled="loading" @click="loadSummary">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="summary-grid">
      <div class="summary-card">
        <span class="card-label">{{ t('evals.total') }}</span>
        <strong class="card-value">{{ summary.total }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.passRate') }}</span>
        <strong class="card-value">{{ passRate }}%</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.avgScore') }}</span>
        <strong class="card-value">{{ formatNum(summary.avg_score) }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.avgLatency') }}</span>
        <strong class="card-value">{{ formatMs(summary.avg_latency_ms) }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.avgCost') }}</span>
        <strong class="card-value">${{ formatCost(summary.avg_cost) }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.toolErrorRate') }}</span>
        <strong class="card-value">{{ formatPct(summary.tool_error_rate) }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.handoffs') }}</span>
        <strong class="card-value">{{ summary.handoff_count ?? 0 }}</strong>
      </div>
      <div class="summary-card">
        <span class="card-label">{{ t('evals.approvals') }}</span>
        <strong class="card-value">{{ summary.approval_count ?? 0 }}</strong>
      </div>
    </div>

    <!-- Trend -->
    <div v-if="summary.trend.length > 0" class="trend-section">
      <h3>{{ t('evals.dailyTrend') }}</h3>
      <div class="trend-chart">
        <div
          v-for="point in summary.trend"
          :key="point.date"
          class="trend-bar-group"
        >
          <div class="trend-bars">
            <div
              class="trend-bar passed"
              :style="{ height: barHeight(point.passed) + 'px' }"
              :title="t('evals.passedCount', { count: point.passed })"
            ></div>
            <div
              class="trend-bar failed"
              :style="{ height: barHeight(point.failed) + 'px' }"
              :title="t('evals.failedCount', { count: point.failed })"
            ></div>
          </div>
          <span class="trend-label">{{ formatDate(point.date) }}</span>
          <span class="trend-score">{{ point.avg_score != null ? point.avg_score.toFixed(0) : '-' }}</span>
        </div>
      </div>
    </div>

    <!-- Runtime Breakdown -->
    <div v-if="summary.by_runtime.length > 0" class="breakdown-section">
      <h3>{{ t('evals.byRuntime') }}</h3>
      <table class="breakdown-table">
        <thead>
          <tr>
            <th>{{ t('runs.runtime') }}</th>
            <th>{{ t('common.total') }}</th>
            <th>{{ t('evals.passed') }}</th>
            <th>{{ t('evals.failed') }}</th>
            <th>{{ t('evals.passRate') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in summary.by_runtime" :key="row.runtime_id">
            <td>{{ row.runtime_name }}</td>
            <td>{{ row.total }}</td>
            <td class="text-passed">{{ row.passed }}</td>
            <td class="text-failed">{{ row.failed }}</td>
            <td>{{ row.avg_score != null ? row.avg_score.toFixed(1) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Config Version Breakdown -->
    <div v-if="summary.by_config_version.length > 0" class="breakdown-section">
      <h3>{{ t('evals.byConfigVersion') }}</h3>
      <table class="breakdown-table">
        <thead>
          <tr>
            <th>{{ t('configVersion.title') }}</th>
            <th>{{ t('common.total') }}</th>
            <th>{{ t('evals.passed') }}</th>
            <th>{{ t('evals.failed') }}</th>
            <th>{{ t('evals.passRate') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in summary.by_config_version" :key="row.config_version">
            <td>{{ row.config_version }}</td>
            <td>{{ row.total }}</td>
            <td class="text-passed">{{ row.passed }}</td>
            <td class="text-failed">{{ row.failed }}</td>
            <td>{{ row.avg_score != null ? row.avg_score.toFixed(1) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-if="!loading && summary.total === 0"
      icon="📊"
      :message="t('evals.noEvals')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { EvalSummaryData, WorkflowRuntime } from '../types'
import { listRuntimes } from '../composables/useWorkflowApi'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

const props = defineProps<{
  summary: EvalSummaryData
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

const runtimes = ref<WorkflowRuntime[]>([])
const selectedRuntime = ref('')

const passRate = computed(() => {
  if (props.summary.total === 0) return '0.0'
  return ((props.summary.passed / props.summary.total) * 100).toFixed(1)
})

const maxTrendRuns = computed(() => {
  return Math.max(1, ...props.summary.trend.map(p => p.runs))
})

function barHeight(count: number): number {
  return Math.max(2, Math.round((count / maxTrendRuns.value) * 60))
}

function formatNum(v: number | null | undefined): string {
  return v != null ? v.toFixed(1) : '-'
}

function formatMs(v: number | null | undefined): string {
  if (v == null) return '-'
  return v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${Math.round(v)}ms`
}

function formatCost(v: number | null | undefined): string {
  return v != null ? v.toFixed(4) : '0.0000'
}

function formatPct(v: number | null | undefined): string {
  return v != null ? (v * 100).toFixed(1) + '%' : '0.0%'
}

function formatDate(dateStr: string): string {
  const parts = dateStr.split('-')
  return `${parts[1]}/${parts[2]}`
}

async function loadRuntimes() {
  try {
    runtimes.value = await listRuntimes()
  } catch {
    // silent
  }
}

function loadSummary() {
  emit('refresh')
}

onMounted(() => {
  loadRuntimes()
})
</script>

<style scoped>
.eval-dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.panel-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  outline: none;
  min-width: 160px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Summary Cards */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* Trend */
.trend-section {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.trend-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.trend-chart {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  min-height: 100px;
}

.trend-bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.trend-bars {
  display: flex;
  gap: 2px;
  align-items: flex-end;
  height: 64px;
}

.trend-bar {
  width: 12px;
  border-radius: 2px 2px 0 0;
  transition: height 0.3s ease;
}

.trend-bar.passed {
  background: var(--color-success, #22c55e);
}

.trend-bar.failed {
  background: var(--color-error, #ef4444);
}

.trend-label {
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
}

.trend-score {
  font-size: 10px;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* Breakdown Tables */
.breakdown-section {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.breakdown-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.breakdown-table {
  width: 100%;
  border-collapse: collapse;
}

.breakdown-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.breakdown-table td {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.breakdown-table tr:last-child td {
  border-bottom: none;
}

.text-passed {
  color: var(--color-success, #22c55e);
  font-weight: 500;
}

.text-failed {
  color: var(--color-error, #ef4444);
  font-weight: 500;
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
