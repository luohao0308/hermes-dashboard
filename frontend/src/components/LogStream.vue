<template>
  <div class="panel">
    <div class="panel-header">
      <h2>实时日志</h2>
      <div class="log-controls">
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <select v-model="levelFilter" class="level-select">
          <option value="all">全部</option>
          <option value="info">信息</option>
          <option value="warning">警告</option>
          <option value="error">错误</option>
        </select>
        <button class="clear-btn" @click="clearLogs">清空</button>
      </div>
    </div>

    <div class="log-stats">
      <span class="stat">
        <span class="stat-dot info"></span>
        {{ infoCount }} 信息
      </span>
      <span class="stat">
        <span class="stat-dot warning"></span>
        {{ warningCount }} 警告
      </span>
      <span class="stat">
        <span class="stat-dot error"></span>
        {{ errorCount }} 错误
      </span>
    </div>

    <div class="log-list" ref="logListRef">
      <div
        v-for="log in filteredLogs"
        :key="log.id"
        class="log-item"
        :class="[log.type, { expanded: expandedLogs.has(log.id) }]"
        @click="toggleExpand(log.id)"
      >
        <div class="log-main">
          <span class="log-icon">{{ logIcon[log.type] }}</span>
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
          <span class="expand-icon">{{ expandedLogs.has(log.id) ? '▼' : '▶' }}</span>
        </div>
        <div class="log-details" v-if="expandedLogs.has(log.id)">
          <div class="detail-row">
            <span class="detail-label">类型:</span>
            <span class="detail-value">{{ logTypeText[log.type] }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">时间:</span>
            <span class="detail-value">{{ log.timestamp }}</span>
          </div>
          <div class="detail-row" v-if="log.source">
            <span class="detail-label">来源:</span>
            <span class="detail-value">{{ log.source }}</span>
          </div>
        </div>
      </div>
      <div v-if="filteredLogs.length === 0 && !loading" class="empty-state">
        <span class="empty-icon">📜</span>
        <span>{{ levelFilter === 'all' ? '暂无日志' : `没有${logTypeText[levelFilter]}级别的日志` }}</span>
      </div>

      <!-- Skeleton Loading -->
      <div class="skeleton" v-if="loading">
        <div class="skeleton-item" v-for="i in 5" :key="i">
          <div class="skeleton-line w-20"></div>
          <div class="skeleton-line w-80"></div>
        </div>
      </div>
    </div>

    <div class="log-footer">
      <span class="log-count">共 {{ filteredLogs.length }} 条日志</span>
      <button class="scroll-top-btn" @click="scrollToTop" v-if="filteredLogs.length > 10">
        ↑ 回到顶部
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface Log {
  id?: number
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error' | 'debug'
  source?: string
}

const props = defineProps<{
  logs: Log[]
  loading?: boolean
}>()

defineEmits<{
  refresh: []
}>()

const MAX_LOGS = 500

const levelFilter = ref<'all' | 'info' | 'warning' | 'error'>('all')
const expandedLogs = ref(new Set<number>())
const logListRef = ref<HTMLElement | null>(null)

const logIcon: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌'
}

const logTypeText: Record<string, string> = {
  info: '信息',
  warning: '警告',
  error: '错误'
}

// Assign IDs to logs
const logsWithId = computed(() => {
  return props.logs.slice(0, MAX_LOGS).map((log, i) => ({
    ...log,
    id: log.id ?? i
  }))
})

const filteredLogs = computed(() => {
  if (levelFilter.value === 'all') return logsWithId.value
  return logsWithId.value.filter(log => log.type === levelFilter.value)
})

const infoCount = computed(() => props.logs.filter(l => l.type === 'info').length)
const warningCount = computed(() => props.logs.filter(l => l.type === 'warning').length)
const errorCount = computed(() => props.logs.filter(l => l.type === 'error').length)

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function toggleExpand(logId: number) {
  if (expandedLogs.value.has(logId)) {
    expandedLogs.value.delete(logId)
  } else {
    expandedLogs.value.add(logId)
  }
}

function clearLogs() {
  expandedLogs.value.clear()
}

function scrollToTop() {
  logListRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
.panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  max-height: 500px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.log-controls {
  display: flex;
  gap: 8px;
}

.level-select {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  padding: 4px 8px;
  font-size: 12px;
  outline: none;
}

.level-select:focus {
  border-color: var(--accent-color);
}

.clear-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.clear-btn:hover {
  background: #fef2f2;
  border-color: var(--error-color);
  color: var(--error-color);
}

.log-stats {
  display: flex;
  gap: 16px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.stat-dot.info { background: var(--accent-color); }
.stat-dot.warning { background: var(--warning-color); }
.stat-dot.error { background: var(--error-color); }

.log-list {
  flex: 1;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  max-height: 320px;
  background: var(--bg-secondary);
}

.log-item {
  padding: 8px 20px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background 0.15s ease;
}

.log-item:hover {
  background: var(--bg-tertiary);
}

.log-main {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.log-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
  font-size: 11px;
}

.log-message {
  color: var(--text-secondary);
  word-break: break-all;
  flex: 1;
  line-height: 1.5;
}

.expand-icon {
  color: var(--text-muted);
  font-size: 10px;
  flex-shrink: 0;
}

.log-item.info .log-message { color: var(--text-secondary); }

.log-item.warning {
  background: #fef3c720;
}

.log-item.warning .log-message { color: var(--warning-color); }

.log-item.error {
  background: #fef2f220;
}

.log-item.error .log-message { color: var(--error-color); }

.log-details {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 11px;
}

.detail-row {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-secondary);
}

.log-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
}

.log-count {
  font-size: 12px;
  color: var(--text-muted);
}

.scroll-top-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.scroll-top-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: var(--text-muted);
  gap: 8px;
  font-size: 13px;
}

.empty-icon {
  font-size: 32px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--border-color);
  color: var(--text-primary);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--border-color);
  border-top-color: var(--text-secondary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Skeleton Loading */
.skeleton .skeleton-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary) 50%, var(--bg-secondary) 75%);
  background-size: 200% 100%;
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
}

.skeleton-line.w-20 { width: 20%; }
.skeleton-line.w-80 { width: 80%; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
