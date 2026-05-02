<template>
  <div class="panel">
    <div class="panel-header">
      <h2>{{ t('approvals.title') }}</h2>
      <div class="header-right">
        <span class="approval-count">{{ total }} {{ t('approvals.title').toLowerCase() }}</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="filter-row">
      <select v-model="statusFilter" class="filter-select" @change="onFilterChange">
        <option value="">{{ t('common.all') }} {{ t('common.status') }}</option>
        <option value="pending">{{ t('approvals.pending') }}</option>
        <option value="approved">{{ t('approvals.approved') }}</option>
        <option value="rejected">{{ t('approvals.rejected') }}</option>
      </select>
      <div v-if="selectedIds.size > 0" class="batch-actions">
        <span class="batch-count">{{ t('approvals.selected', { count: selectedIds.size }) }}</span>
        <button class="action-btn approve-btn" @click="$emit('batchApprove', [...selectedIds])" :disabled="actionLoading">
          {{ t('approvals.batchApprove') }}
        </button>
        <button class="action-btn reject-btn" @click="$emit('batchReject', [...selectedIds])" :disabled="actionLoading">
          {{ t('approvals.batchReject') }}
        </button>
        <button class="clear-btn" @click="clearSelection">{{ t('common.close') }}</button>
      </div>
    </div>

    <div class="approval-list">
      <div
        v-for="item in approvals"
        :key="item.id"
        class="approval-item"
        :class="{ selected: selectedIds.has(item.id) }"
      >
        <label v-if="item.status === 'pending'" class="item-checkbox">
          <input
            type="checkbox"
            :checked="selectedIds.has(item.id)"
            @change="toggleSelect(item.id)"
          />
        </label>
        <div class="item-main">
          <div class="item-info">
            <span class="item-status" :class="'status-' + item.status">
              {{ statusIcon(item.status) }}
            </span>
            <div class="item-details">
              <span class="item-title">{{ item.reason || 'Approval request' }}</span>
              <span class="item-id">{{ item.id }}</span>
            </div>
          </div>
          <div class="item-meta">
            <span v-if="item.requested_by" class="item-requester">
              by {{ item.requested_by }}
            </span>
            <span class="item-date">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
        <div v-if="item.status === 'pending'" class="item-actions">
          <button
            class="action-btn approve-btn"
            @click.stop="$emit('approve', item.id)"
            :disabled="actionLoading"
          >
            {{ t('approvals.approve') }}
          </button>
          <button
            class="action-btn reject-btn"
            @click.stop="$emit('reject', item.id)"
            :disabled="actionLoading"
          >
            {{ t('approvals.reject') }}
          </button>
        </div>
        <div v-if="item.status !== 'pending'" class="item-resolution">
          <span class="resolution-status" :class="'status-' + item.status">
            {{ item.status }}
          </span>
          <span v-if="item.resolved_by" class="resolver">
            by {{ item.resolved_by }}
          </span>
          <span v-if="item.resolved_note" class="note">
            {{ item.resolved_note }}
          </span>
        </div>
      </div>

      <!-- Skeleton Loading -->
      <LoadingState v-if="loading" :message="t('approvals.loadingApprovals')" />

      <EmptyState v-if="approvals.length === 0 && !loading" :message="t('approvals.noApprovals')" />
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
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} / {{ total }}
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
import type { ApprovalItem } from '../types'
import { formatDate } from '../composables/useFormatters'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

defineProps<{
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

const statusFilter = ref('')
const selectedIds = ref(new Set<string>())

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

function statusIcon(status: string): string {
  switch (status) {
    case 'approved': return '✅'
    case 'pending': return '⏳'
    case 'rejected': return '❌'
    default: return '❓'
  }
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

.approval-count {
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

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.batch-count {
  font-size: 12px;
  color: var(--accent-color);
  font-weight: 600;
}

.clear-btn {
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-muted);
}

.clear-btn:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
}

.item-checkbox {
  display: flex;
  align-items: center;
  margin-right: 8px;
  cursor: pointer;
}

.item-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--accent-color);
}

.approval-item.selected {
  background: var(--accent-soft);
}

.approval-list {
  display: flex;
  flex-direction: column;
  max-height: 500px;
  overflow-y: auto;
}

.approval-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
}

.approval-item:hover {
  background: var(--bg-secondary);
}

.approval-item:last-child {
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

.item-requester {
  font-size: 12px;
  color: var(--text-secondary);
}

.item-date {
  font-size: 11px;
  color: var(--text-muted);
}

.item-actions {
  display: flex;
  gap: 8px;
  margin-left: 16px;
}

.action-btn {
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
}

.approve-btn {
  background: #16a34a;
  color: white;
  border-color: #16a34a;
}

.approve-btn:hover:not(:disabled) {
  background: #15803d;
}

.reject-btn {
  background: #dc2626;
  color: white;
  border-color: #dc2626;
}

.reject-btn:hover:not(:disabled) {
  background: #b91c1c;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.item-resolution {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
}

.resolution-status {
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.resolution-status.status-approved {
  background: rgba(22, 163, 74, 0.15);
  color: #16a34a;
}

.resolution-status.status-rejected {
  background: rgba(220, 38, 38, 0.15);
  color: #dc2626;
}

.resolver {
  font-size: 11px;
  color: var(--text-muted);
}

.note {
  font-size: 11px;
  color: var(--text-secondary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

