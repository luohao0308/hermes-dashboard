<template>
  <div class="panel">
    <h2>实时日志</h2>
    <div class="log-list">
      <div v-for="(log, index) in logs" :key="index" class="log-item" :class="log.type">
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      <div v-if="logs.length === 0" class="empty-state">
        暂无日志
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Log {
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error'
}

defineProps<{
  logs: Log[]
}>()

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
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
}

.panel h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #f8fafc;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  font-family: monospace;
  font-size: 0.875rem;
  max-height: 300px;
}

.log-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.375rem 0;
  border-bottom: 1px solid #1e293b;
}

.log-time {
  color: #64748b;
  flex-shrink: 0;
}

.log-message {
  color: #e2e8f0;
  word-break: break-all;
}

.log-item.warning .log-message {
  color: #fde68a;
}

.log-item.error .log-message {
  color: #fca5a5;
}

.empty-state {
  color: #64748b;
  text-align: center;
  padding: 2rem;
}
</style>
