<template>
  <div class="panel">
    <div class="panel-header">
      <h2>当前任务</h2>
      <div class="header-actions">
        <span class="task-count">{{ tasks.length }} 个任务</span>
        <button class="refresh-btn" @click="emit('refresh')" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="filter-bar">
      <button
        v-for="filter in filters"
        :key="filter.value"
        class="filter-btn"
        :class="{ active: activeFilter === filter.value }"
        @click="activeFilter = filter.value"
      >
        {{ filter.label }}
      </button>
    </div>

    <div class="task-list" v-if="!loading && filteredTasks.length > 0">
      <div
        v-for="task in filteredTasks"
        :key="task.task_id"
        class="task-item"
        :class="task.status"
      >
        <div class="task-main">
          <div class="task-info">
            <span class="task-name">{{ task.name }}</span>
            <span class="task-id">#{{ task.task_id }}</span>
          </div>
          <span class="task-status-badge" :class="task.status">
            {{ statusText[task.status] }}
          </span>
        </div>

        <div class="progress-section">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :class="task.status"
              :style="{ width: task.progress + '%' }"
            ></div>
          </div>
          <div class="progress-info">
            <span class="progress-text">{{ task.progress }}%</span>
          </div>
        </div>

        <div class="task-actions" v-if="task.status === 'running'">
          <button class="action-btn pause" @click="emit('pause', task.task_id)">
            ⏸ 暂停
          </button>
          <button class="action-btn cancel" @click="emit('cancel', task.task_id)">
            ✕ 取消
          </button>
        </div>
      </div>
    </div>

    <!-- Skeleton Loading -->
    <div class="task-list skeleton" v-else-if="loading">
      <div class="skeleton-item" v-for="i in 3" :key="i">
        <div class="skeleton-line w-60"></div>
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-progress"></div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <span class="empty-icon">📋</span>
      <span>{{ emptyMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface Task {
  task_id: string
  name: string
  status: 'running' | 'pending' | 'completed'
  progress: number
  started_at?: string
  estimated_end?: string
  message_count?: number
  model?: string
}

const props = defineProps<{
  tasks: Task[]
  loading?: boolean
}>()

const emit = defineEmits<{
  pause: [taskId: string]
  cancel: [taskId: string]
  refresh: []
}>()

const filters = [
  { label: '全部', value: 'all' },
  { label: '运行中', value: 'running' },
  { label: '等待中', value: 'pending' },
  { label: '已完成', value: 'completed' }
]

const activeFilter = ref('all')

const statusText: Record<string, string> = {
  running: '运行中',
  pending: '等待中',
  completed: '已完成'
}

const filteredTasks = computed(() => {
  if (activeFilter.value === 'all') return props.tasks
  return props.tasks.filter(t => t.status === activeFilter.value)
})

const emptyMessage = computed(() => {
  const messages: Record<string, string> = {
    all: '暂无任务',
    running: '没有运行中的任务',
    pending: '没有等待中的任务',
    completed: '没有已完成的任务'
  }
  return messages[activeFilter.value]
})
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: #334155;
  color: #e2e8f0;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.8rem;
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
  width: 12px;
  height: 12px;
  border: 2px solid #64748b;
  border-top-color: #e2e8f0;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.filter-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.filter-btn {
  padding: 0.375rem 0.75rem;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.375rem;
  color: #94a3b8;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  border-color: #475569;
  color: #e2e8f0;
}

.filter-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.task-count {
  font-size: 0.75rem;
  color: #64748b;
  background: #0f172a;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.task-item {
  padding: 1rem;
  background: #0f172a;
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.task-item:hover {
  background: #1e293b;
}

.task-item.running {
  border-left: 3px solid #3b82f6;
}

.task-item.pending {
  border-left: 3px solid #f59e0b;
}

.task-item.completed {
  border-left: 3px solid #22c55e;
}

.task-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.task-name {
  font-weight: 500;
  color: #e2e8f0;
}

.task-id {
  font-size: 0.7rem;
  color: #64748b;
  font-family: monospace;
}

.task-status-badge {
  padding: 0.2rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 500;
}

.task-status-badge.running {
  background: #3b82f620;
  color: #60a5fa;
}

.task-status-badge.pending {
  background: #f59e0b20;
  color: #fbbf24;
}

.task-status-badge.completed {
  background: #22c55e20;
  color: #4ade80;
}

.progress-section {
  margin-bottom: 0.75rem;
}

.progress-bar {
  height: 6px;
  background: #1e293b;
  border-radius: 0.25rem;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  border-radius: 0.25rem;
  transition: width 0.3s ease;
}

.progress-fill.running {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.progress-fill.pending {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.progress-fill.completed {
  background: linear-gradient(90deg, #22c55e, #4ade80);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.progress-text {
  color: #94a3b8;
  font-family: monospace;
}

.task-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid #1e293b;
}

.action-btn {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.pause {
  background: #3b82f620;
  color: #60a5fa;
}

.action-btn.pause:hover {
  background: #3b82f640;
}

.action-btn.cancel {
  background: #ef444420;
  color: #f87171;
}

.action-btn.cancel:hover {
  background: #ef444440;
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

/* Skeleton Loading */
.skeleton .skeleton-item {
  padding: 1rem;
  background: #0f172a;
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  border-radius: 0.25rem;
  animation: shimmer 1.5s infinite;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }

.skeleton-progress {
  height: 6px;
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  border-radius: 0.25rem;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
