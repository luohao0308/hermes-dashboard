<template>
  <div class="panel">
    <div class="panel-header">
      <div>
        <h2>{{ t('approvals.title') }}</h2>
        <p class="panel-subtitle">Review and authorize sensitive tool executions.</p>
      </div>
      <div class="header-right">
        <span class="approval-count">{{ total }} {{ t('approvals.title').toLowerCase() }}</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="filter-row">
      <div class="search-shell">
        <Search :size="16" />
        <input v-model="searchText" type="search" placeholder="Filter current page by approval, run, requester or reason..." />
      </div>
      <select v-model="statusFilter" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('common.status') }}</option>
        <option value="pending">{{ t('approvals.pending') }}</option>
        <option value="approved">{{ t('approvals.approved') }}</option>
        <option value="rejected">{{ t('approvals.rejected') }}</option>
      </select>
      <div v-if="selectedIds.size > 0" class="batch-actions">
        <span>{{ t('approvals.selected', { count: selectedIds.size }) }}</span>
        <button class="approve-action approve-btn" @click="$emit('batchApprove', [...selectedIds])" :disabled="actionLoading">
          <Check :size="14" />
          {{ t('approvals.batchApprove') }}
        </button>
        <button class="reject-action reject-btn" @click="$emit('batchReject', [...selectedIds])" :disabled="actionLoading">
          <X :size="14" />
          {{ t('approvals.batchReject') }}
        </button>
        <button class="clear-btn" @click="clearSelection">{{ t('common.close') }}</button>
      </div>
    </div>

    <div v-if="filteredApprovals.length > 0" class="approval-list">
      <article
        v-for="item in filteredApprovals"
        :key="item.id"
        class="approval-card"
        :class="{ selected: selectedIds.has(item.id), resolved: item.status !== 'pending' }"
      >
        <div class="approval-main">
          <label v-if="item.status === 'pending'" class="item-checkbox">
            <input :checked="selectedIds.has(item.id)" type="checkbox" @change="toggleSelect(item.id)" />
          </label>
          <div class="tool-icon">
            <ShieldCheck v-if="item.status === 'approved'" :size="20" />
            <XCircle v-else-if="item.status === 'rejected'" :size="20" />
            <AlertTriangle v-else :size="20" />
          </div>
          <div class="approval-copy">
            <div class="approval-title-row">
              <h3>{{ item.reason || 'Approval request' }}</h3>
              <span :class="['risk-badge', riskTone(item)]">{{ item.status }}</span>
            </div>
            <p class="payload-line">
              <span class="mono">{{ item.id }}</span>
              <span v-if="item.run_id">run: {{ shortId(item.run_id) }}</span>
              <span v-if="item.tool_call_id">tool: {{ shortId(item.tool_call_id) }}</span>
            </p>
            <div class="approval-meta">
              <span>
                <User :size="13" />
                {{ item.requested_by || 'unknown requester' }}
              </span>
              <span>
                <Clock3 :size="13" />
                {{ formatDate(item.created_at) }}
              </span>
            </div>
          </div>
        </div>

        <div class="approval-side">
          <div v-if="item.status === 'pending'" class="item-actions">
            <button class="approve-action approve-btn" @click.stop="$emit('approve', item.id)" :disabled="actionLoading">
              <Check :size="15" />
              {{ t('approvals.approve') }}
            </button>
            <button class="reject-action reject-btn" @click.stop="$emit('reject', item.id)" :disabled="actionLoading">
              <X :size="15" />
              {{ t('approvals.reject') }}
            </button>
          </div>
          <div v-else class="resolution">
            <span :class="['resolution-status', item.status]">{{ item.status }}</span>
            <small v-if="item.resolved_by">by {{ item.resolved_by }}</small>
            <p v-if="item.resolved_note">{{ item.resolved_note }}</p>
          </div>
        </div>
      </article>
    </div>

    <LoadingState v-if="loading" :message="t('approvals.loadingApprovals')" />
    <EmptyState v-if="filteredApprovals.length === 0 && !loading" :message="emptyMessage" />

    <div v-if="total > limit" class="pagination">
      <button class="page-btn" :disabled="offset === 0" @click="goToPage(offset - limit)">
        {{ t('common.prev') }}
      </button>
      <span class="page-info">
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} / {{ total }}
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
import { AlertTriangle, Check, Clock3, Search, ShieldCheck, User, X, XCircle } from 'lucide-vue-next'
import type { ApprovalItem } from '../types'
import { formatDate } from '../composables/useFormatters'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

const props = defineProps<{
  approvals: ApprovalItem[]
  total: number
  limit: number
  offset: number
  loading?: boolean
  actionLoading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  approve: [id: string]
  reject: [id: string]
  filterChange: [status: string]
  pageChange: [offset: number]
  batchApprove: [ids: string[]]
  batchReject: [ids: string[]]
}>()

const searchText = ref('')
const statusFilter = ref('')
const selectedIds = ref(new Set<string>())

const filteredApprovals = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  if (!q) return props.approvals
  return props.approvals.filter((item) => [
    item.id,
    item.run_id,
    item.tool_call_id || '',
    item.reason || '',
    item.requested_by || '',
  ].some((value) => value.toLowerCase().includes(q)))
})

const emptyMessage = computed(() => (
  searchText.value.trim()
    ? 'No approvals match this current page filter.'
    : t('approvals.noApprovals')
))

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

function riskTone(item: ApprovalItem): string {
  if (item.status === 'approved') return 'approved'
  if (item.status === 'rejected') return 'rejected'
  if (item.reason?.toLowerCase().includes('destructive')) return 'critical'
  return 'pending'
}

function shortId(id: string): string {
  return id.length > 12 ? id.slice(0, 8) : id
}

function onFilterChange() {
  emit('filterChange', statusFilter.value)
}

function goToPage(newOffset: number) {
  emit('pageChange', Math.max(0, newOffset))
}
</script>

<style scoped>
.panel {
  overflow: hidden;
}

.panel-header,
.filter-row,
.header-right,
.search-shell,
.batch-actions,
.approval-main,
.approval-title-row,
.approval-meta,
.item-actions,
.pagination {
  display: flex;
  align-items: center;
}

.panel-header {
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

.header-right {
  gap: 12px;
}

.approval-count,
.page-info {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
}

.refresh-btn,
.page-btn,
.approve-action,
.reject-action,
.clear-btn {
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

.refresh-btn,
.page-btn,
.clear-btn {
  padding: 0 12px;
}

.filter-row {
  gap: 10px;
  padding: 14px 18px;
}

.search-shell {
  flex: 1;
  min-width: 240px;
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
  font-weight: 800;
}

.batch-actions {
  gap: 8px;
  margin-left: auto;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.approval-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
}

.approval-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: var(--shadow-sm);
}

.approval-card.selected {
  border-color: #93c5fd;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.1);
}

.approval-main {
  gap: 14px;
  min-width: 0;
}

.item-checkbox input {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
}

.tool-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: 0 0 42px;
  border-radius: 12px;
  background: #fff7ed;
  color: #ea580c;
}

.approval-copy {
  min-width: 0;
  flex: 1;
}

.approval-title-row {
  gap: 10px;
  justify-content: space-between;
}

.approval-title-row h3 {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.risk-badge {
  flex-shrink: 0;
  padding: 4px 8px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.risk-badge.pending {
  color: #b45309;
  background: #fffbeb;
  border-color: #fde68a;
}

.risk-badge.critical,
.risk-badge.rejected {
  color: #be123c;
  background: #fff1f2;
  border-color: #fecdd3;
}

.risk-badge.approved {
  color: #047857;
  background: #ecfdf5;
  border-color: #bbf7d0;
}

.payload-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 7px 0;
  color: #64748b;
  font-size: 11px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 800;
}

.approval-meta {
  flex-wrap: wrap;
  gap: 12px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.approval-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.approval-side {
  min-width: 220px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.item-actions {
  gap: 8px;
}

.approve-action {
  padding: 0 12px;
  color: #ffffff;
  background: #059669;
  border-color: #059669;
}

.reject-action {
  padding: 0 12px;
  color: #be123c;
  background: #ffffff;
  border-color: #fecdd3;
}

.approve-action:disabled,
.reject-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.resolution {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  color: #64748b;
  font-size: 12px;
}

.resolution-status {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.resolution-status.approved {
  color: #047857;
  background: #ecfdf5;
}

.resolution-status.rejected {
  color: #be123c;
  background: #fff1f2;
}

.pagination {
  justify-content: space-between;
  padding: 14px 18px;
  border-top: 1px solid var(--border-subtle);
  background: #f8fafc;
}

.page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
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
  .filter-row,
  .approval-card {
    align-items: stretch;
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .approval-side,
  .resolution {
    align-items: stretch;
    min-width: 0;
  }
}
</style>
