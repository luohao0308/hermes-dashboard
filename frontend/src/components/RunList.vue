<template>
  <div class="panel">
    <div class="panel-header">
      <h2>{{ t('runs.title') }}</h2>
      <div class="header-right">
        <span class="run-count">{{ total }} {{ t('runs.title').toLowerCase() }}</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="filter-row">
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

    <div class="run-list">
      <div
        v-for="run in runs"
        :key="run.id"
        class="run-item"
        @click="$emit('selectRun', run.id)"
      >
        <div class="item-main">
          <div class="item-info">
            <span class="item-status" :class="'status-' + run.status">
              {{ statusIcon(run.status) }}
            </span>
            <div class="item-details">
              <span class="item-title">{{ run.title }}</span>
              <span class="item-id">{{ run.id }}</span>
            </div>
          </div>
          <div class="item-meta">
            <span v-if="run.duration_ms != null" class="item-duration">
              {{ formatDuration(run.duration_ms) }}
            </span>
            <span v-if="run.total_tokens != null" class="item-tokens">
              {{ formatNumber(run.total_tokens) }} tokens
            </span>
            <span class="item-date">{{ formatDate(run.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Skeleton Loading -->
      <LoadingState v-if="loading" :message="t('runs.loadingRuns')" />

      <EmptyState v-if="runs.length === 0 && !loading" :message="t('runs.noRuns')" />
    </div>

    <div v-if="total > limit" class="pagination">
      <button
        class="page-btn"
        :disabled="offset === 0"
        @click="goToPage(offset - limit)"
      >
        {{ t('common.prev') }}
      </button>
      <span class="page-info">
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} of {{ total }}
      </span>
      <button
        class="page-btn"
        :disabled="offset + limit >= total"
        @click="goToPage(offset + limit)"
      >
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WorkflowRun, WorkflowRuntime } from '../types'
import { formatDate, formatDuration, formatNumber } from '../composables/useFormatters'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

defineProps<{
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

const statusFilter = ref('')
const runtimeFilter = ref('')
const connectorTypeFilter = ref('')

function statusIcon(status: string): string {
  switch (status) {
    case 'completed': return '✅'
    case 'running': return '⏳'
    case 'queued': return '📋'
    case 'error': return '❌'
    default: return '❓'
  }
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
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.run-count {
  font-size: 12px;
  color: var(--text-muted);
}

.filter-row {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.filter-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  outline: none;
  transition: all 0.2s ease;
  min-width: 140px;
}

.filter-select:focus {
  border-color: var(--accent-color);
}

.run-list {
  display: flex;
  flex-direction: column;
  max-height: 500px;
  overflow-y: auto;
}

.run-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.2s ease;
}

.run-item:hover {
  background: var(--bg-secondary);
}

.run-item:last-child {
  border-bottom: none;
}

.item-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.item-status {
  font-size: 20px;
}

.item-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.item-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.item-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.item-duration {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.item-tokens {
  font-size: 11px;
  color: var(--text-muted);
}

.item-date {
  font-size: 11px;
  color: var(--text-muted);
}


.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
}

.page-btn {
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

.page-btn:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
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

</style>
