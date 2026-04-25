<template>
  <div class="panel">
    <div class="panel-header">
      <h2>历史任务</h2>
      <button class="refresh-btn" @click="$emit('refresh')" :disabled="loading">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </div>
    <div class="history-list">
      <div v-for="item in history" :key="item.task_id" class="history-item">
        <div class="history-info">
          <span class="history-name">{{ item.name }}</span>
          <span class="history-meta">
            {{ formatDate(item.completed_at) }}
            <span v-if="item.model"> · {{ item.model }}</span>
            <span v-if="item.message_count"> · {{ item.message_count }} 条消息</span>
          </span>
        </div>
        <div class="history-right">
          <span class="history-duration">{{ formatDuration(item.duration) }}</span>
          <span v-if="item.input_tokens || item.output_tokens" class="history-tokens">
            ↑{{ item.input_tokens || 0 }} ↓{{ item.output_tokens || 0 }}
          </span>
        </div>
      </div>
      <div v-if="history.length === 0" class="empty-state">
        <span class="empty-icon">📋</span>
        <span>暂无历史任务</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface HistoryItem {
  task_id: string
  name: string
  completed_at: string
  duration: number
  message_count?: number
  model?: string
  input_tokens?: number
  output_tokens?: number
}

defineProps<{
  history: HistoryItem[]
  loading?: boolean
}>()

defineEmits<{
  refresh: []
}>()

function formatDate(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
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

.panel h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f8fafc;
  margin: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0f172a;
  border-radius: 0.5rem;
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.history-name {
  font-weight: 500;
  color: #e2e8f0;
}

.history-meta {
  font-size: 0.75rem;
  color: #64748b;
}

.history-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.history-duration {
  font-size: 0.875rem;
  color: #94a3b8;
  font-family: monospace;
}

.history-tokens {
  font-size: 0.7rem;
  color: #64748b;
  font-family: monospace;
}

.empty-state {
  color: #64748b;
  text-align: center;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
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
