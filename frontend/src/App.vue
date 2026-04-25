<template>
  <div class="app-container">
    <header class="app-header">
      <h1>Hermès 工作状态监控</h1>
      <div class="connection-status" :class="{ connected: isConnected }">
        <span class="status-dot"></span>
        {{ isConnected ? '已连接' : '未连接' }}
      </div>
    </header>
    <main class="app-main">
      <TaskPanel
        :tasks="tasks"
        @pause="handlePause"
        @cancel="handleCancel"
      />
      <LogStream :logs="logs" />
      <HistoryList :history="history" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import TaskPanel from './components/TaskPanel.vue'
import LogStream from './components/LogStream.vue'
import HistoryList from './components/HistoryList.vue'

interface Task {
  task_id: string
  name: string
  status: 'running' | 'pending' | 'completed'
  progress: number
  started_at?: string
  elapsed?: number
}

interface Log {
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error'
}

interface HistoryItem {
  task_id: string
  name: string
  completed_at: string
  duration: number
}

const isConnected = ref(false)
const tasks = ref<Task[]>([])
const logs = ref<Log[]>([])
const history = ref<HistoryItem[]>([])
let eventSource: EventSource | null = null

function handlePause(taskId: string) {
  console.log('Pause task:', taskId)
}

function handleCancel(taskId: string) {
  console.log('Cancel task:', taskId)
}

onMounted(() => {
  // 初始化示例数据
  tasks.value = [
    { task_id: '1', name: '数据同步', status: 'running', progress: 45, started_at: new Date(Date.now() - 120000).toISOString() },
    { task_id: '2', name: '模型训练', status: 'pending', progress: 0 },
    { task_id: '3', name: '报告生成', status: 'completed', progress: 100, started_at: new Date(Date.now() - 300000).toISOString() }
  ]

  // 连接 SSE
  eventSource = new EventSource('http://localhost:8000/sse')

  eventSource.addEventListener('connected', () => {
    isConnected.value = true
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: '已连接到 Hermès 服务',
      type: 'info'
    })
  })

  eventSource.addEventListener('task_update', (event) => {
    const data = JSON.parse(event.data)
    const index = tasks.value.findIndex(t => t.task_id === data.task_id)
    if (index >= 0) {
      tasks.value[index] = data
    } else {
      tasks.value.push(data)
    }
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: `任务更新: ${data.name} - ${data.progress}%`,
      type: 'info'
    })
  })

  eventSource.addEventListener('system_status', (event) => {
    const data = JSON.parse(event.data)
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: `系统状态: ${data.status}, 活跃连接: ${data.active_connections}`,
      type: 'info'
    })
  })

  eventSource.addEventListener('heartbeat', () => {
    // 心跳保持连接
  })

  eventSource.onerror = () => {
    isConnected.value = false
    logs.value.unshift({
      timestamp: new Date().toISOString(),
      message: '连接断开，正在重连...',
      type: 'warning'
    })
  }
})

onUnmounted(() => {
  eventSource?.close()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #0f172a;
  color: #e2e8f0;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.app-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f8fafc;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #94a3b8;
}

.connection-status.connected {
  color: #4ade80;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.connection-status.connected .status-dot {
  background: #4ade80;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.app-main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
}
</style>
