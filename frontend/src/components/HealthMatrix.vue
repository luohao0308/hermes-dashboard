<template>
  <div class="health-matrix">
    <div class="matrix-header">
      <h3>{{ t('health.title') }}</h3>
      <button class="btn btn-sm" @click="$emit('refresh')" :disabled="loading">
        {{ loading ? t('common.loading') : t('common.refresh') }}
      </button>
    </div>

    <LoadingState v-if="loading" :message="t('health.checking')" />

    <div v-else-if="health" class="health-grid">
      <!-- Overall Status -->
      <div class="health-row overall" :class="statusClass(health.status)">
        <span class="health-icon">{{ statusIcon(health.status) }}</span>
        <span class="health-label">{{ t('health.overall') }}</span>
        <span class="health-value">{{ health.status }}</span>
      </div>

      <!-- Database -->
      <div class="health-row" :class="statusClass(health.database?.status === 'connected' ? 'healthy' : 'error')">
        <span class="health-icon">{{ statusIcon(health.database?.status === 'connected' ? 'healthy' : 'error') }}</span>
        <span class="health-label">{{ t('health.database') }}</span>
        <span class="health-value">
          {{ health.database?.status || 'unknown' }}
          <span v-if="health.database?.migration_version" class="health-detail">
            migration: {{ health.database.migration_version.slice(0, 8) }}
          </span>
        </span>
      </div>

      <!-- Workers -->
      <div
        v-for="(worker, name) in health.workers"
        :key="name"
        class="health-row"
        :class="statusClass(worker.status === 'alive' ? 'healthy' : worker.status === 'unknown' ? 'warning' : 'error')"
      >
        <span class="health-icon">{{ statusIcon(worker.status === 'alive' ? 'healthy' : worker.status === 'unknown' ? 'warning' : 'error') }}</span>
        <span class="health-label">{{ name }}</span>
        <span class="health-value">
          {{ worker.status }}
          <span v-if="worker.last_seen_seconds_ago != null" class="health-detail">
            {{ formatAge(worker.last_seen_seconds_ago) }}
          </span>
        </span>
      </div>

      <!-- API Info -->
      <div class="health-row">
        <span class="health-icon">ℹ</span>
        <span class="health-label">{{ t('health.apiVersion') }}</span>
        <span class="health-value">{{ health.version || 'N/A' }}</span>
      </div>

      <div class="health-row">
        <span class="health-icon">ℹ</span>
        <span class="health-label">{{ t('health.activeConnections') }}</span>
        <span class="health-value">{{ health.active_connections ?? 'N/A' }}</span>
      </div>
    </div>

    <!-- Metrics Section -->
    <div v-if="metrics" class="metrics-section">
      <h4 class="metrics-title">{{ t('health.metrics') }}</h4>
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-value">{{ metrics.runs?.total ?? 0 }}</span>
          <span class="metric-label">{{ t('health.totalRuns') }}</span>
        </div>
        <div class="metric-card running">
          <span class="metric-value">{{ metrics.runs?.running ?? 0 }}</span>
          <span class="metric-label">{{ t('health.running') }}</span>
        </div>
        <div class="metric-card failed">
          <span class="metric-value">{{ metrics.runs?.failed ?? 0 }}</span>
          <span class="metric-label">{{ t('health.failed') }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ metrics.approvals?.pending ?? 0 }}</span>
          <span class="metric-label">{{ t('health.pendingApprovals') }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ metrics.tasks?.dead_letter ?? 0 }}</span>
          <span class="metric-label">{{ t('health.deadLetter') }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ metrics.connectors?.errors_today ?? 0 }}</span>
          <span class="metric-label">{{ t('health.connectorErrors') }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ metrics.evals?.total ?? 0 }}</span>
          <span class="metric-label">{{ t('health.evalResults') }}</span>
        </div>
      </div>
    </div>

    <EmptyState v-if="!health && !metrics" icon="🏥" :message="t('health.noData')" />
  </div>
</template>

<script setup lang="ts">
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'
import { useI18n } from "vue-i18n"
const { t } = useI18n()

interface HealthData {
  status: string
  version?: string
  active_connections?: number
  database?: {
    status: string
    migration_version?: string | null
    error?: string | null
  }
  workers?: Record<string, {
    status: string
    last_seen_seconds_ago?: number | null
    error?: string
  }>
  timestamp?: string
}

interface MetricsData {
  runs?: { total: number; running: number; failed: number; completed: number }
  approvals?: { pending: number }
  tasks?: { dead_letter: number }
  connectors?: { errors_today: number }
  evals?: { total: number }
  workers?: Record<string, { status: string; age_seconds?: number | null }>
}

defineProps<{
  health: HealthData | null
  metrics?: MetricsData | null
  loading?: boolean
}>()

defineEmits<{
  refresh: []
}>()

function statusClass(status: string): string {
  if (status === 'healthy') return 'status-healthy'
  if (status === 'degraded' || status === 'warning' || status === 'stale') return 'status-warning'
  return 'status-error'
}

function statusIcon(status: string): string {
  if (status === 'healthy') return '✓'
  if (status === 'degraded' || status === 'warning' || status === 'stale') return '⚠'
  return '✗'
}

function formatAge(seconds: number): string {
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}
</script>

<style scoped>
.health-matrix {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.matrix-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.matrix-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.health-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.health-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  font-size: 13px;
}

.health-row.overall {
  font-weight: 600;
}

.health-icon {
  width: 20px;
  text-align: center;
  font-size: 14px;
}

.status-healthy .health-icon { color: #6ee7b7; }
.status-warning .health-icon { color: #fbbf24; }
.status-error .health-icon { color: #fca5a5; }

.health-label {
  flex: 1;
  color: var(--text-secondary);
}

.health-value {
  color: var(--text-primary);
  font-weight: 500;
  text-align: right;
}

.health-detail {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
  margin-left: 8px;
}

.btn {
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
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

.metrics-section {
  margin-top: 8px;
}

.metrics-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
}

.metric-card.running .metric-value { color: #60a5fa; }
.metric-card.failed .metric-value { color: #fca5a5; }

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
