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
        v-for="(log, index) in filteredLogs"
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
      <div v-if="filteredLogs.length === 0" class="empty-state">
        <span class="empty-icon">📜</span>
        <span>{{ levelFilter === 'all' ? '暂无日志' : `没有${logTypeText[levelFilter]}级别的日志` }}</span>
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
  type: 'info' | 'warning' | 'error'
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
let logIdCounter = 0

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
  background: #1e293b;
  border-radius: 0.75rem;
  padding: 1.25rem;
  border: 1px solid #334155;
  display: flex;
  flex-direction: column;
  max-height: 500px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.panel-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f8fafc;
  margin: 0;
}

.log-controls {
  display: flex;
  gap: 0.5rem;
}

.level-select {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.375rem;
  color: #e2e8f0;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.clear-btn {
  background: #334155;
  border: none;
  border-radius: 0.375rem;
  color: #94a3b8;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #ef4444;
  color: #fff;
}

.log-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
}

.stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #94a3b8;
}

.stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.stat-dot.info {
  background: #3b82f6;
}

.stat-dot.warning {
  background: #f59e0b;
}

.stat-dot.error {
  background: #ef4444;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.8125rem;
  max-height: 320px;
}

.log-item {
  padding: 0.5rem;
  border-radius: 0.375rem;
  margin-bottom: 0.25rem;
  cursor: pointer;
  transition: background 0.2s;
}

.log-item:hover {
  background: #334155;
}

.log-main {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}

.log-icon {
  flex-shrink: 0;
}

.log-time {
  color: #64748b;
  flex-shrink: 0;
  font-size: 0.75rem;
}

.log-message {
  color: #e2e8f0;
  word-break: break-all;
  flex: 1;
}

.expand-icon {
  color: #64748b;
  font-size: 0.625rem;
  flex-shrink: 0;
}

.log-item.info .log-message {
  color: #93c5fd;
}

.log-item.warning {
  background: rgba(245, 158, 11, 0.1);
}

.log-item.warning .log-message {
  color: #fde68a;
}

.log-item.error {
  background: rgba(239, 68, 68, 0.1);
}

.log-item.error .log-message {
  color: #fca5a5;
}

.log-details {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #0f172a;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.detail-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  color: #64748b;
  flex-shrink: 0;
}

.detail-value {
  color: #94a3b8;
}

.log-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #334155;
}

.log-count {
  font-size: 0.75rem;
  color: #64748b;
}

.scroll-top-btn {
  background: transparent;
  border: 1px solid #334155;
  border-radius: 0.25rem;
  color: #94a3b8;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  cursor: pointer;
}

.scroll-top-btn:hover {
  background: #334155;
  color: #e2e8f0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: #64748b;
  gap: 0.5rem;
}

.empty-icon {
  font-size: 2rem;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  background: #334155;
  color: #e2e8f0;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #475569;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #64748b;
  border-top-color: #e2e8f0;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
