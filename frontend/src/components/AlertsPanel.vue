<template>
  <section class="alerts-panel">
    <div class="alerts-header">
      <div>
        <h2>告警与建议</h2>
        <p>{{ subtitle }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '同步中' : '刷新' }}
      </button>
    </div>

    <div class="alerts-list">
      <article v-for="alert in alerts" :key="alert.id" class="alert-item" :class="alert.severity">
        <div class="severity-mark"></div>
        <div class="alert-body">
          <div class="alert-title-row">
            <strong>{{ alert.title }}</strong>
            <span>{{ severityText[alert.severity] || alert.severity }}</span>
          </div>
          <p>{{ alert.message }}</p>
          <div class="alert-meta">
            <span>{{ alert.source }}</span>
            <span v-if="alert.session_id">#{{ alert.session_id.slice(0, 8) }}</span>
            <span>{{ formatTime(alert.created_at) }}</span>
          </div>
        </div>
        <div class="alert-actions">
          <button v-if="alert.session_id" class="action-btn" @click="emit('runbook', alert)">
            生成 Runbook
          </button>
          <button class="action-btn" @click="emit('action', alert)">
            {{ alert.action_label }}
          </button>
        </div>
      </article>

      <div v-if="alerts.length === 0 && !loading" class="empty-alerts">
        暂无告警
      </div>

      <div v-if="loading" class="loading-stack">
        <div v-for="i in 2" :key="i" class="skeleton-row"></div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface AlertItem {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  source: string
  session_id?: string | null
  action_label: string
  action_nav: string
  created_at: string
}

const props = defineProps<{
  alerts: AlertItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  action: [alert: AlertItem]
  runbook: [alert: AlertItem]
}>()

const severityText: Record<string, string> = {
  critical: '严重',
  warning: '关注',
  info: '信息',
}

const subtitle = computed(() => {
  const critical = props.alerts.filter(alert => alert.severity === 'critical').length
  const warning = props.alerts.filter(alert => alert.severity === 'warning').length
  if (critical > 0) return `${critical} 个严重告警需要优先处理`
  if (warning > 0) return `${warning} 个运行信号建议关注`
  return '当前没有需要立即介入的告警'
})

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.alerts-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.alerts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.alerts-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
}

.alerts-header p {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.alerts-list {
  display: flex;
  flex-direction: column;
}

.alert-item {
  display: grid;
  grid-template-columns: 4px minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.alert-item:last-child {
  border-bottom: 0;
}

.severity-mark {
  width: 4px;
  height: 52px;
  border-radius: 999px;
  background: var(--accent-color);
}

.alert-item.critical .severity-mark {
  background: var(--error-color);
}

.alert-item.warning .severity-mark {
  background: var(--warning-color);
}

.alert-item.info .severity-mark {
  background: var(--success-color);
}

.alert-body {
  min-width: 0;
}

.alert-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-title-row strong {
  color: var(--text-primary);
  font-size: 13px;
}

.alert-title-row span {
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
}

.alert-body p {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
}

.refresh-btn,
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.alert-actions {
  display: flex;
  gap: 8px;
}

.action-btn:hover,
.refresh-btn:hover:not(:disabled) {
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.empty-alerts {
  padding: 18px 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.loading-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 24px;
}

.skeleton-row {
  height: 70px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-secondary) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .alerts-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .alert-item {
    grid-template-columns: 4px 1fr;
  }

  .action-btn {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
