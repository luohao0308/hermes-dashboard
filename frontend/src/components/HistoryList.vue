<template>
  <div class="panel">
    <div class="panel-header">
      <h2>历史任务</h2>
      <div class="header-right">
        <span class="history-count">{{ filteredHistory.length }} 个任务</span>
        <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="history-stats">
      <div class="stat-card">
        <span class="stat-value">{{ history.length }}</span>
        <span class="stat-label">总任务数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ totalDuration }}</span>
        <span class="stat-label">总时长</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ avgDuration }}</span>
        <span class="stat-label">平均时长</span>
      </div>
    </div>

    <div class="filter-row">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索任务名称..."
        class="search-input"
      />
      <select v-model="sortBy" class="sort-select">
        <option value="completed_at">按完成时间</option>
        <option value="duration">按时长</option>
        <option value="name">按名称</option>
      </select>
    </div>

    <div class="history-list">
      <div
        v-for="item in filteredHistory"
        :key="item.task_id"
        class="history-item"
      >
        <div class="item-main">
          <div class="item-info">
            <span class="item-status" :class="item.status">{{ statusIcon[item.status] }}</span>
            <div class="item-details">
              <span class="item-name">{{ item.name }}</span>
              <span class="item-id">#{{ item.task_id }}</span>
            </div>
          </div>
          <div class="item-meta">
            <span class="item-duration">{{ formatDuration(item.duration) }}</span>
            <span class="item-date">{{ formatDate(item.completed_at) }}</span>
          </div>
        </div>
        <div class="item-actions">
          <button class="action-btn" @click="viewDetails(item)" title="查看详情">
            👁
          </button>
          <button class="action-btn" @click="reRunTask(item)" title="重新运行">
            🔄
          </button>
        </div>
      </div>
      <!-- Skeleton Loading -->
      <div class="skeleton" v-if="loading">
        <div class="skeleton-item" v-for="i in 3" :key="i">
          <div class="skeleton-left">
            <div class="skeleton-line w-50"></div>
            <div class="skeleton-line w-30"></div>
          </div>
          <div class="skeleton-right">
            <div class="skeleton-line w-20"></div>
          </div>
        </div>
      </div>
      <div v-if="filteredHistory.length === 0 && !loading" class="empty-state">
        <span class="empty-icon">📋</span>
        <span>{{ searchQuery ? '没有匹配的任务' : '暂无历史任务' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface HistoryItem {
  task_id: string
  name: string
  completed_at: string
  duration: number
  status: 'success' | 'failed' | 'cancelled'
  message_count?: number
  model?: string
  input_tokens?: number
  output_tokens?: number
}

const props = defineProps<{
  history: HistoryItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
  viewDetails: [item: HistoryItem]
  reRunTask: [item: HistoryItem]
}>()

const searchQuery = ref('')
const sortBy = ref<'completed_at' | 'duration' | 'name'>('completed_at')

const statusIcon: Record<string, string> = {
  success: '✅',
  failed: '❌',
  cancelled: '⚠️'
}

const filteredHistory = computed(() => {
  let result = [...props.history]

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item =>
      item.name.toLowerCase().includes(query) ||
      item.task_id.toLowerCase().includes(query)
    )
  }

  result.sort((a, b) => {
    switch (sortBy.value) {
      case 'completed_at':
        return new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()
      case 'duration':
        return b.duration - a.duration
      case 'name':
        return a.name.localeCompare(b.name)
      default:
        return 0
    }
  })

  return result
})

const totalDuration = computed(() => {
  const total = props.history.reduce((sum, item) => sum + item.duration, 0)
  return formatDuration(total)
})

const avgDuration = computed(() => {
  if (props.history.length === 0) return '0s'
  const avg = Math.floor(props.history.reduce((sum, item) => sum + item.duration, 0) / props.history.length)
  return formatDuration(avg)
})

function formatDate(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins < 60) return `${mins}m ${secs}s`
  const hours = Math.floor(mins / 60)
  const remainingMins = mins % 60
  return `${hours}h ${remainingMins}m`
}

function viewDetails(item: HistoryItem) {
  emit('viewDetails', item)
}

function reRunTask(item: HistoryItem) {
  emit('reRunTask', item)
}
</script>

<style scoped>
.panel {
  background: #1e293b;
  border-radius: 0.75rem;
  padding: 1.25rem;
  border: 1px solid #334155;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.panel-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f8fafc;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.history-count {
  font-size: 0.75rem;
  color: #64748b;
  background: #0f172a;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
}

.history-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat-card {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 0.75rem;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 600;
  color: #f8fafc;
  font-family: monospace;
}

.stat-label {
  font-size: 0.625rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.filter-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-input {
  flex: 1;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #e2e8f0;
}

.search-input::placeholder {
  color: #64748b;
}

.sort-select {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #e2e8f0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0f172a;
  border-radius: 0.5rem;
  transition: background 0.2s;
}

.history-item:hover {
  background: #1e293b;
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
  gap: 0.75rem;
}

.item-status {
  font-size: 1.25rem;
}

.item-details {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.item-name {
  font-weight: 500;
  color: #e2e8f0;
}

.item-id {
  font-size: 0.75rem;
  color: #64748b;
  font-family: monospace;
}

.item-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.item-duration {
  font-size: 0.875rem;
  color: #94a3b8;
  font-family: monospace;
}

.item-date {
  font-size: 0.75rem;
  color: #64748b;
}

.item-actions {
  display: flex;
  gap: 0.25rem;
  margin-left: 1rem;
}

.action-btn {
  background: transparent;
  border: none;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.action-btn:hover {
  opacity: 1;
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

/* Skeleton Loading */
.skeleton .skeleton-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0f172a;
  border-radius: 0.5rem;
}

.skeleton-left {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skeleton-right {
  display: flex;
  align-items: center;
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  border-radius: 0.25rem;
  animation: shimmer 1.5s infinite;
}

.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-30 { width: 30%; }
.skeleton-line.w-20 { width: 40px; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
