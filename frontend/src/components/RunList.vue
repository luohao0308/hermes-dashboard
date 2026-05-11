<template>
  <div class="panel">
    <div class="panel-header">
      <div>
        <h2>{{ t('runs.title') }}</h2>
        <p class="panel-subtitle">Realtime execution traces, costs, tokens and failure context.</p>
      </div>
      <div class="header-right">
        <span class="run-count">{{ total }} {{ t('runs.title').toLowerCase() }}</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="filter-row">
      <div class="search-shell">
        <Search :size="16" />
        <input v-model="searchText" type="search" placeholder="Filter current page by run title or ID..." />
      </div>
      <select v-model="statusFilter" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('common.status') }}</option>
        <option value="queued">{{ t('status.pending') }}</option>
        <option value="running">{{ t('status.running') }}</option>
        <option value="completed">{{ t('status.completed') }}</option>
        <option value="error">{{ t('status.failed') }}</option>
      </select>
      <select v-model="runtimeFilter" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('runs.runtime') }}</option>
        <option v-for="rt in runtimes" :key="rt.id" :value="rt.id">
          {{ rt.name }}
        </option>
      </select>
      <select v-model="connectorTypeFilter" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('connectors.connectorType') }}</option>
        <option v-for="ct in connectorTypes" :key="ct" :value="ct">
          {{ ct }}
        </option>
      </select>
    </div>

    <div v-if="filteredRuns.length > 0" class="table-wrap">
      <table class="runs-table">
        <thead>
          <tr>
            <th>{{ t('runs.runId') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.status') }}</th>
            <th class="numeric">{{ t('runs.cost') }}</th>
            <th>{{ t('runs.tokens') }}</th>
            <th>{{ t('runs.duration') }}</th>
            <th>{{ t('runs.startTime') }}</th>
            <th class="center">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in filteredRuns" :key="run.id" class="run-item" @click="$emit('selectRun', run.id)">
            <td class="mono">{{ shortId(run.id) }}</td>
            <td>
              <div class="run-title-cell">
                <span>{{ run.title }}</span>
                <small>{{ run.runtime_id }}</small>
              </div>
            </td>
            <td>
              <span :class="['status-badge', statusTone(run.status)]">
                <component :is="statusIcon(run.status)" :size="12" />
                {{ run.status }}
              </span>
            </td>
            <td class="numeric">{{ formatCost(run.total_cost) }}</td>
            <td>{{ run.total_tokens != null ? `${formatNumber(run.total_tokens)} tokens` : '-' }}</td>
            <td>{{ run.duration_ms != null ? formatDuration(run.duration_ms) : '-' }}</td>
            <td>{{ formatDate(run.created_at) }}</td>
            <td class="center">
              <button class="icon-action" type="button" @click.stop="$emit('selectRun', run.id)">
                <ExternalLink :size="15" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <LoadingState v-if="loading" :message="t('runs.loadingRuns')" />
    <EmptyState v-if="filteredRuns.length === 0 && !loading" :message="emptyMessage" />

    <div v-if="total > limit" class="pagination">
      <button class="page-btn" :disabled="offset === 0" @click="goToPage(offset - limit)">
        {{ t('common.prev') }}
      </button>
      <span class="page-info">
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} of {{ total }}
      </span>
      <button class="page-btn" :disabled="offset + limit >= total" @click="goToPage(offset + limit)">
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, Clock3, ExternalLink, Loader2, Search, XCircle } from 'lucide-vue-next'
import type { Component } from 'vue'
import type { WorkflowRun, WorkflowRuntime } from '../types'
import { formatDate, formatDuration, formatNumber } from '../composables/useFormatters'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

const props = defineProps<{
  runs: WorkflowRun[]
  runtimes: WorkflowRuntime[]
  connectorTypes?: string[]
  total: number
  limit: number
  offset: number
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  selectRun: [id: string]
  filterChange: [filters: { status: string; runtime_id: string; connector_type: string }]
  pageChange: [offset: number]
}>()

const searchText = ref('')
const statusFilter = ref('')
const runtimeFilter = ref('')
const connectorTypeFilter = ref('')

const filteredRuns = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  if (!q) return props.runs
  return props.runs.filter((run) =>
    run.id.toLowerCase().includes(q) || run.title.toLowerCase().includes(q)
  )
})

const emptyMessage = computed(() => (
  searchText.value.trim()
    ? 'No runs match this current page filter.'
    : t('runs.noRuns')
))

function statusIcon(status: string): Component {
  if (status === 'completed') return CheckCircle2
  if (status === 'running') return Loader2
  if (status === 'queued') return Clock3
  if (status === 'error' || status === 'failed') return XCircle
  return Clock3
}

function statusTone(status: string): string {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'running'
  if (status === 'error' || status === 'failed') return 'failed'
  return 'queued'
}

function formatCost(value: number | null | undefined): string {
  return value == null ? '-' : `$${value.toFixed(4)}`
}

function shortId(id: string): string {
  return id.length > 12 ? id.slice(0, 8) : id
}

function onFilterChange() {
  emit('filterChange', {
    status: statusFilter.value,
    runtime_id: runtimeFilter.value,
    connector_type: connectorTypeFilter.value,
  })
}

function goToPage(newOffset: number) {
  emit('pageChange', Math.max(0, newOffset))
}
</script>

<style scoped>
.panel {
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h2 {
  margin: 0;
}

.panel-subtitle {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
}

.header-right,
.filter-row,
.search-shell,
.status-badge,
.pagination {
  display: flex;
  align-items: center;
}

.header-right {
  gap: 12px;
}

.run-count {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
}

.refresh-btn,
.page-btn,
.icon-action {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
  font-weight: 700;
}

.refresh-btn {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  font-size: 12px;
}

.filter-row {
  gap: 10px;
  padding: 14px 18px;
}

.search-shell {
  flex: 1;
  min-width: 220px;
  height: 38px;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: #94a3b8;
}

.search-shell input {
  flex: 1;
  min-width: 0;
  border: 0;
  box-shadow: none;
}

.filter-select {
  height: 38px;
  min-width: 150px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.table-wrap {
  overflow-x: auto;
}

.runs-table {
  width: 100%;
  border-collapse: collapse;
}

.runs-table th {
  padding: 12px 18px;
  color: #94a3b8;
  background: #f8fafc;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
}

.runs-table td {
  padding: 14px 18px;
  border-top: 1px solid var(--border-subtle);
  color: #475569;
  font-size: 12px;
}

.runs-table tbody tr {
  cursor: pointer;
  transition: background 0.16s ease;
}

.runs-table tbody tr:hover {
  background: #f8fafc;
}

.mono {
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 800;
}

.run-title-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.run-title-cell span {
  color: #0f172a;
  font-weight: 800;
}

.run-title-cell small {
  color: #94a3b8;
  font-size: 10px;
}

.status-badge {
  width: fit-content;
  gap: 6px;
  padding: 4px 9px;
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

.numeric {
  text-align: right;
}

.center {
  text-align: center;
}

.icon-action {
  width: 30px;
  height: 30px;
  display: inline-grid;
  place-items: center;
}

.pagination {
  justify-content: space-between;
  padding: 14px 18px;
  border-top: 1px solid var(--border-subtle);
  background: #f8fafc;
}

.page-btn {
  min-height: 30px;
  padding: 0 12px;
  font-size: 12px;
}

.page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.page-info {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #dbeafe;
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .panel-header,
  .filter-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
