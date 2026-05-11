<template>
  <div class="panel">
    <div class="panel-header">
      <div>
        <h2>{{ t('connectors.failedEvents') }}</h2>
        <p class="subtitle">{{ t('connectors.failedEvents') }}</p>
      </div>
      <div class="header-right">
        <span class="event-count">{{ total }} {{ t('status.failed') }}</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Connector Selector -->
    <div class="filter-row">
      <select v-model="selectedConnectorId" class="filter-select" @change="onConnectorChange">
        <option value="">{{ t('connectors.selectConnector') }}...</option>
        <option v-for="c in connectors" :key="c.id" :value="c.id">
          {{ c.display_name }} ({{ c.connector_type }})
        </option>
      </select>
    </div>

    <div class="event-list">
      <div v-for="item in events" :key="item.id" class="event-item">
        <div class="event-main">
          <div class="event-info">
            <span class="event-type">{{ item.event_type }}</span>
            <span v-if="item.event_id" class="event-id">{{ item.event_id }}</span>
          </div>
          <div class="event-error">{{ item.error_message }}</div>
          <div class="event-meta">
            <span v-if="item.run_id" class="meta-tag">run: {{ item.run_id.slice(0, 8) }}</span>
            <span class="meta-date">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
        <div class="event-actions">
          <button
            class="action-btn replay-btn"
            @click="$emit('replay', item.id)"
            :disabled="replayingId === item.id"
          >
            <span v-if="replayingId === item.id" class="spinner"></span>
            {{ replayingId === item.id ? t('common.processing') : t('connectors.replayEvent') }}
          </button>
        </div>
      </div>

      <LoadingState v-if="loading" :message="t('connectors.loadingFailedEvents')" />
      <EmptyState v-if="events.length === 0 && !loading" :message="t('connectors.noFailedEvents')" />
    </div>

    <div v-if="events.length > 0" class="pagination">
      <button class="page-btn" :disabled="offset === 0" @click="$emit('prevPage')">
        {{ t('common.prev') }}
      </button>
      <span class="page-info">
        {{ offset + 1 }}–{{ offset + events.length }} / {{ total }}
      </span>
      <button class="page-btn" :disabled="!hasMore" @click="$emit('nextPage')">
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ConnectorConfig, FailedEventItem } from '../types'
import { formatDate } from '../composables/useFormatters'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

defineProps<{
  events: FailedEventItem[]
  connectors: ConnectorConfig[]
  total: number
  limit: number
  offset: number
  hasMore?: boolean
  loading?: boolean
  replayingId?: string
}>()

const emit = defineEmits<{
  refresh: []
  replay: [eventId: string]
  connectorChange: [connectorId: string]
  pageChange: [offset: number]
  nextPage: []
  prevPage: []
}>()

const selectedConnectorId = ref('')

function onConnectorChange() {
  if (selectedConnectorId.value) {
    emit('connectorChange', selectedConnectorId.value)
  }
}

</script>

<style scoped>
.panel {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-header h2 {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
}

.subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.event-count {
  font-size: 12px;
  color: #b91c1c;
  font-weight: 900;
}

.filter-row {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: #f8fafc;
  border-bottom: 1px solid var(--border-subtle);
}

.filter-select {
  min-height: 38px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
  outline: none;
  min-width: 200px;
  box-shadow: var(--shadow-sm);
}

.filter-select:focus {
  border-color: var(--accent-color);
}

.event-list {
  display: flex;
  flex-direction: column;
  max-height: 500px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.2s;
}

.event-item:hover {
  background: #f8fafc;
}

.event-item:last-child {
  border-bottom: none;
}

.event-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.event-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.event-type {
  font-size: 13px;
  font-weight: 900;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.event-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.event-error {
  font-size: 12px;
  color: #b91c1c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 500px;
}

.event-meta {
  display: flex;
  gap: 10px;
  align-items: center;
}

.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.meta-date {
  font-size: 11px;
  color: var(--text-muted);
}

.event-actions {
  margin-left: 16px;
  flex-shrink: 0;
}

.action-btn {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
}

.replay-btn {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.replay-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  min-height: 34px;
  padding: 0 14px;
  background: #ffffff;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
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
  min-height: 34px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  background: #ffffff;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
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

@media (max-width: 720px) {
  .panel-header,
  .header-right,
  .event-item {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-select,
  .refresh-btn,
  .action-btn {
    width: 100%;
    justify-content: center;
  }

  .event-actions {
    margin-left: 0;
  }

  .event-error {
    max-width: none;
    white-space: normal;
  }
}
</style>
