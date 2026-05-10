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
          <span v-if="worker.worker_id" class="health-detail">
            {{ worker.worker_id }}
          </span>
          <span v-if="worker.pid" class="health-detail">
            pid {{ worker.pid }}
          </span>
          <span v-if="worker.version" class="health-detail">
            v{{ worker.version }}
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
      <div v-if="metrics.workers" class="worker-metrics">
        <div v-for="(worker, name) in metrics.workers" :key="name" class="worker-card">
          <span class="worker-name">{{ name }}</span>
          <strong>{{ worker.status }}</strong>
          <small v-if="worker.age_seconds != null">{{ formatAge(worker.age_seconds) }}</small>
          <small v-if="worker.worker_id">{{ worker.worker_id }}</small>
          <small v-if="worker.pid">pid {{ worker.pid }}</small>
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
    worker_id?: string | null
    pid?: number | null
    version?: string | null
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
  workers?: Record<string, {
    status: string
    age_seconds?: number | null
    worker_id?: string | null
    pid?: number | null
    version?: string | null
  }>
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
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
}

.health-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: #ffffff;
  box-shadow: var(--glass-shadow);
}

.health-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #ffffff;
  font-size: 13px;
  border-bottom: 1px solid var(--border-subtle);
}

.health-row:last-child {
  border-bottom: none;
}

.health-row.overall {
  font-weight: 900;
  background: #f8fafc;
}

.health-icon {
  width: 20px;
  text-align: center;
  font-size: 14px;
}

.status-healthy .health-icon { color: #047857; }
.status-warning .health-icon { color: #d97706; }
.status-error .health-icon { color: #b91c1c; }

.health-label {
  flex: 1;
  color: var(--text-secondary);
}

.health-value {
  color: var(--text-primary);
  font-weight: 800;
  text-align: right;
}

.health-detail {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
  margin-left: 8px;
}

.btn {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: #ffffff;
  color: var(--text-secondary);
  transition: all 0.2s;
  box-shadow: var(--shadow-sm);
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
  font-weight: 900;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.worker-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.worker-card {
  display: flex;
  flex-direction: column;
  gap: 3px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: #ffffff;
  box-shadow: var(--shadow-sm);
  padding: 12px;
}

.worker-name {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.worker-card strong {
  color: var(--text-primary);
  font-size: 13px;
}

.worker-card small {
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: var(--radius-lg);
  background: #ffffff;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
}

.metric-card.running .metric-value { color: #2563eb; }
.metric-card.failed .metric-value { color: #b91c1c; }

.metric-value {
  font-size: 20px;
  font-weight: 900;
  color: var(--text-primary);
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  text-align: center;
}

@media (max-width: 640px) {
  .matrix-header,
  .health-row {
    align-items: stretch;
    flex-direction: column;
  }

  .health-value {
    text-align: left;
  }
}
</style>
