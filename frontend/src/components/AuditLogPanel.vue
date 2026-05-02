<template>
  <div class="audit-panel">
    <div class="panel-header">
      <h2>{{ t('audit.title') }}</h2>
      <div class="header-actions">
        <div class="export-group">
          <button class="btn btn-secondary" @click="exportJSON" :disabled="logs.length === 0" :title="t('audit.exportJson')">
            JSON
          </button>
          <button class="btn btn-secondary" @click="exportCSV" :disabled="logs.length === 0" :title="t('audit.exportCsv')">
            CSV
          </button>
        </div>
        <button class="btn btn-secondary" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Quick filter chips -->
    <div class="quick-filters" v-if="hasActiveFilters">
      <span class="quick-label">{{ t('audit.active') }}:</span>
      <span
        v-for="chip in activeChips"
        :key="chip.key"
        class="filter-chip"
        @click="clearFilter(chip.key)"
      >
        {{ chip.label }}: {{ chip.value }}
        <span class="chip-close">&times;</span>
      </span>
      <button class="chip-clear-all" @click="clearAllFilters">{{ t('audit.clearAll') }}</button>
    </div>

    <!-- Filters -->
    <div class="filter-row">
      <select v-model="filters.actor_type" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('audit.actor') }}</option>
        <option value="user">{{ t('users.title').split(' ')[0] }}</option>
        <option value="system">{{ t('nav.system') }}</option>
        <option value="connector">{{ t('connectors.title') }}</option>
      </select>
      <select v-model="filters.resource_type" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('audit.resourceType') }}</option>
        <option value="workflow">Workflow</option>
        <option value="connector">Connector</option>
        <option value="approval">Approval</option>
        <option value="eval">Eval</option>
        <option value="run">Run</option>
        <option value="user">User</option>
        <option value="environment">Environment</option>
      </select>
      <select v-model="filters.action" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('audit.action') }}</option>
        <option value="created">{{ t('audit.created') }}</option>
        <option value="updated">{{ t('audit.updated') }}</option>
        <option value="deleted">{{ t('audit.deleted') }}</option>
        <option value="approved">{{ t('audit.approved') }}</option>
        <option value="rejected">{{ t('audit.rejected') }}</option>
      </select>
      <input
        v-model="filters.actor_id"
        class="filter-input"
        :placeholder="t('audit.actorIdPlaceholder')"
        @change="onFilterChange"
      />
      <input
        v-model="filters.resource_id"
        class="filter-input filter-input-sm"
        :placeholder="t('audit.resourceIdPlaceholder')"
        @change="onFilterChange"
      />
    </div>

    <!-- Content -->
    <LoadingState v-if="loading" :message="t('audit.loadingLogs')" />

    <EmptyState
      v-else-if="logs.length === 0"
      icon="📋"
      :message="t('audit.noLogs')"
    />

    <div v-else class="audit-table-wrapper">
      <table class="audit-table">
        <thead>
          <tr>
            <th>{{ t('common.time') }}</th>
            <th>{{ t('audit.actor') }}</th>
            <th>{{ t('audit.action') }}</th>
            <th>{{ t('audit.resourceType') }}</th>
            <th>{{ t('common.details') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in logs" :key="entry.id">
            <td class="cell-time">{{ formatTime(entry.created_at) }}</td>
            <td class="cell-actor">
              <span class="actor-badge">{{ entry.actor_type || '-' }}</span>
              <span class="actor-id">{{ entry.actor_id || '-' }}</span>
            </td>
            <td class="cell-action">
              <span class="action-badge" :class="actionClass(entry.action)">
                {{ entry.action }}
              </span>
            </td>
            <td class="cell-resource">
              <span class="resource-type">{{ entry.resource_type }}</span>
              <span v-if="entry.resource_id" class="resource-id">{{ entry.resource_id.slice(0, 8) }}</span>
            </td>
            <td class="cell-summary">{{ entry.summary || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="total > limit" class="pagination">
      <button class="page-btn" :disabled="offset === 0" @click="goToPage(offset - limit)">
        {{ t('common.prev') }}
      </button>
      <span class="page-info">
        {{ offset + 1 }}-{{ Math.min(offset + limit, total) }} / {{ total }}
      </span>
      <button class="page-btn" :disabled="offset + limit >= total" @click="goToPage(offset + limit)">
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

interface AuditLogEntry {
  id: string
  actor_type: string | null
  actor_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  summary: string | null
  created_at: string
}

const props = defineProps<{
  logs: AuditLogEntry[]
  total: number
  limit: number
  offset: number
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  filterChange: [filters: { actor_type: string; actor_id: string; action: string; resource_type: string; resource_id: string }]
  pageChange: [offset: number]
}>()

const filters = ref({
  actor_type: '',
  actor_id: '',
  action: '',
  resource_type: '',
  resource_id: '',
})

const FILTER_LABELS: Record<string, string> = {
  actor_type: t('audit.filterActor'),
  actor_id: t('audit.filterActorId'),
  action: t('audit.filterAction'),
  resource_type: t('audit.filterResource'),
  resource_id: t('audit.filterRequestId'),
}

const hasActiveFilters = computed(() =>
  Object.values(filters.value).some(v => v !== ''),
)

const activeChips = computed(() =>
  Object.entries(filters.value)
    .filter(([, v]) => v !== '')
    .map(([key, value]) => ({ key, label: FILTER_LABELS[key] ?? key, value })),
)

function onFilterChange() {
  emit('filterChange', { ...filters.value })
}

function clearFilter(key: string) {
  ;(filters.value as Record<string, string>)[key] = ''
  onFilterChange()
}

function clearAllFilters() {
  filters.value = { actor_type: '', actor_id: '', action: '', resource_type: '', resource_id: '' }
  onFilterChange()
}

function goToPage(newOffset: number) {
  emit('pageChange', newOffset)
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function actionClass(action: string): string {
  if (action.includes('create')) return 'action-create'
  if (action.includes('update')) return 'action-update'
  if (action.includes('delete')) return 'action-delete'
  if (action.includes('approve')) return 'action-approve'
  if (action.includes('reject')) return 'action-reject'
  return ''
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function exportJSON() {
  const data = JSON.stringify(props.logs, null, 2)
  downloadBlob(data, `audit-logs-${Date.now()}.json`, 'application/json')
}

function escapeCSV(value: string | null): string {
  if (value == null) return ''
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function exportCSV() {
  const headers = [t('audit.csvTime'), t('audit.csvActorType'), t('audit.csvActorId'), t('audit.csvAction'), t('audit.csvResourceType'), t('audit.csvResourceId'), t('audit.csvSummary')]
  const rows = props.logs.map(entry => [
    escapeCSV(entry.created_at),
    escapeCSV(entry.actor_type),
    escapeCSV(entry.actor_id),
    escapeCSV(entry.action),
    escapeCSV(entry.resource_type),
    escapeCSV(entry.resource_id),
    escapeCSV(entry.summary),
  ].join(','))
  const csv = [headers.join(','), ...rows].join('\n')
  downloadBlob(csv, `audit-logs-${Date.now()}.csv`, 'text/csv')
}
</script>

<style scoped>
.audit-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.filter-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-select,
.filter-input {
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  min-width: 140px;
}

.filter-input {
  flex: 1;
  min-width: 200px;
}

.filter-input-sm {
  min-width: 160px;
  flex: 0.8;
}

.audit-table-wrapper {
  overflow-x: auto;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.audit-table th {
  text-align: left;
  padding: 10px 12px;
  color: var(--text-muted);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-subtle);
}

.audit-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.cell-time {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  white-space: nowrap;
}

.cell-actor {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.actor-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
}

.actor-id {
  font-size: 12px;
  color: var(--text-secondary);
}

.action-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.action-create { background: #065f46; color: #6ee7b7; }
.action-update { background: #1e3a5f; color: #93c5fd; }
.action-delete { background: #7f1d1d; color: #fca5a5; }
.action-approve { background: #065f46; color: #6ee7b7; }
.action-reject { background: #7f1d1d; color: #fca5a5; }

.cell-resource {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.resource-type {
  font-weight: 500;
  color: var(--text-primary);
}

.resource-id {
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--text-muted);
}

.cell-summary {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
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

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  transition: all 0.2s;
}

.btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.export-group {
  display: flex;
  gap: 4px;
}

.export-group .btn {
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.quick-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--accent-soft);
  color: var(--accent-color);
  border-radius: var(--radius-pill);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-chip:hover {
  background: var(--accent-color);
  color: #fff;
}

.chip-close {
  font-size: 14px;
  line-height: 1;
  margin-left: 2px;
}

.chip-clear-all {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.chip-clear-all:hover {
  color: var(--text-primary);
}
</style>
