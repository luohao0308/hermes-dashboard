<template>
  <div class="panel">
    <h2>历史任务</h2>
    <div class="history-list">
      <div v-for="item in history" :key="item.task_id" class="history-item">
        <div class="history-info">
          <span class="history-name">{{ item.name }}</span>
          <span class="history-time">{{ formatDate(item.completed_at) }}</span>
        </div>
        <span class="history-duration">{{ formatDuration(item.duration) }}</span>
      </div>
      <div v-if="history.length === 0" class="empty-state">
        暂无历史任务
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
}

defineProps<{
  history: HistoryItem[]
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

.panel h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #f8fafc;
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

.history-time {
  font-size: 0.75rem;
  color: #64748b;
}

.history-duration {
  font-size: 0.875rem;
  color: #94a3b8;
  font-family: monospace;
}

.empty-state {
  color: #64748b;
  text-align: center;
  padding: 2rem;
}
</style>
