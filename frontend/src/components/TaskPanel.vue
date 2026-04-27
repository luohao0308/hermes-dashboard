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
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.filter-bar {
  display: flex;
  gap: 6px;
  padding: 16px 24px;
  background: var(--bg-secondary);
}

.filter-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.filter-btn.active {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.task-count {
  font-size: 12px;
  color: var(--text-muted);
}

.task-list {
  display: flex;
  flex-direction: column;
}

.task-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
}

.task-item:last-child {
  border-bottom: none;
}

.task-item:hover {
  background: var(--bg-secondary);
}

.task-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.task-id {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.task-status-badge {
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
}

.task-status-badge.running {
  background: var(--accent-soft);
  color: var(--accent-color);
}

.task-status-badge.pending {
  background: var(--warning-soft);
  color: var(--warning-color);
}

.task-status-badge.completed {
  background: var(--success-soft);
  color: var(--success-color);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-fill.running {
  background: var(--gradient-prism);
}

.progress-fill.pending {
  background: var(--warning-color);
}

.progress-fill.completed {
  background: var(--success-color);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.progress-text {
  color: var(--text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
  min-width: 36px;
  text-align: right;
}

.task-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn.pause {
  background: var(--accent-soft);
  color: var(--accent-color);
}

.action-btn.pause:hover {
  background: var(--accent-color);
  color: white;
}

.action-btn.cancel {
  background: var(--error-soft);
  color: var(--error-color);
}

.action-btn.cancel:hover {
  background: var(--error-color);
  color: white;
}

.empty-state {
  color: var(--text-muted);
  text-align: center;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.empty-icon {
  font-size: 32px;
}

/* Skeleton Loading */
.skeleton .skeleton-item {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary) 50%, var(--bg-secondary) 75%);
  background-size: 200% 100%;
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }

.skeleton-progress {
  height: 6px;
  background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary) 50%, var(--bg-secondary) 75%);
  background-size: 200% 100%;
  border-radius: 3px;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
