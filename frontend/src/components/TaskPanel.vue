<template>
  <div class="panel">
    <h2>当前任务</h2>
    <div class="task-list">
      <div v-for="task in tasks" :key="task.task_id" class="task-item">
        <div class="task-header">
          <span class="task-name">{{ task.name }}</span>
          <span class="task-status" :class="task.status">{{ statusText[task.status] }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
        </div>
        <span class="progress-text">{{ task.progress }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Task {
  task_id: string
  name: string
  status: 'running' | 'pending' | 'completed'
  progress: number
}

defineProps<{
  tasks: Task[]
}>()

const statusText: Record<string, string> = {
  running: '运行中',
  pending: '等待中',
  completed: '已完成'
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

.task-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 1rem;
}

.task-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.task-name {
  font-weight: 500;
  color: #e2e8f0;
}

.task-status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: #334155;
  color: #94a3b8;
}

.task-status.running {
  background: #1d4ed8;
  color: #93c5fd;
}

.task-status.pending {
  background: #713f12;
  color: #fde68a;
}

.task-status.completed {
  background: #14532d;
  color: #86efac;
}

.progress-bar {
  height: 0.5rem;
  background: #334155;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 0.25rem;
  display: block;
}
</style>
