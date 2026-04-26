<template>
  <div class="agent-panel">
    <!-- Header -->
    <div class="agent-header">
      <div class="agent-title">🤖 Agent 工作台</div>
      <div class="agent-actions">
        <button class="btn-refresh" @click="fetchAgents" :disabled="loading">
          刷新
        </button>
      </div>
    </div>

    <!-- Agent Cards Grid -->
    <div class="agent-cards">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
        :class="`status-${agent.status}`"
      >
        <div class="agent-card-header">
          <div class="agent-name">{{ agent.name }}</div>
          <div class="agent-status-badge" :class="agent.status">
            <span class="status-dot-sm"></span>
            {{ agent.status }}
          </div>
        </div>

        <div class="agent-card-meta">
          <div class="meta-item">
            <span class="meta-label">Role:</span>
            <span class="meta-value">{{ agent.role }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Events:</span>
            <span class="meta-value">{{ agent.event_count }}</span>
          </div>
          <div class="meta-item" v-if="agent.last_error">
            <span class="meta-label">Error:</span>
            <span class="meta-value error">{{ agent.last_error }}</span>
          </div>
        </div>

        <!-- Recent logs for this agent -->
        <div class="agent-logs" v-if="agentLogs[agent.id]?.length">
          <div
            v-for="(log, i) in agentLogs[agent.id].slice(-5)"
            :key="i"
            class="agent-log-line"
            :class="log.type"
          >
            {{ log.text }}
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="agents.length === 0 && !loading" class="agent-empty">
        暂无 Agent 连接<br>
        <small>Agent 系统已启动，正在初始化...</small>
      </div>
    </div>

    <!-- Hermes Alerts -->
    <div class="alerts-section" v-if="alerts.length">
      <div class="alerts-title">⚠️ Hermès 告警</div>
      <div
        v-for="alert in alerts"
        :key="alert.id"
        class="alert-item"
        :class="alert.level"
      >
        <span class="alert-time">{{ alert.time }}</span>
        <span class="alert-msg">{{ alert.message }}</span>
      </div>
    </div>

    <!-- Message Input -->
    <div class="agent-input-section">
      <div class="input-label">💬 发送消息给 TriageAgent:</div>
      <div class="input-row">
        <input
          v-model="inputMessage"
          class="agent-input"
          placeholder="例如: check hermes status, why did my session fail, ..."
          @keyup.enter="sendMessage"
          :disabled="sending"
        />
        <button
          class="btn-send"
          @click="sendMessage"
          :disabled="sending || !inputMessage.trim()"
        >
          {{ sending ? '发送中...' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const API_BASE = 'http://localhost:8000'

interface AgentInfo {
  id: string
  name: string
  role: string
  status: 'idle' | 'running' | 'error' | 'done'
  status_message?: string
  event_count: number
  last_error?: string
  created_at: string
}

interface AgentLog {
  id: string
  type: 'output' | 'handoff' | 'error' | 'status'
  text: string
  time: string
}

interface Alert {
  id: string
  level: 'info' | 'warning' | 'error'
  message: string
  time: string
  session_id?: string
}

const agents = ref<AgentInfo[]>([])
const agentLogs = ref<Record<string, AgentLog[]>>({})
const alerts = ref<Alert[]>([])
const inputMessage = ref('')
const loading = ref(false)
const sending = ref(false)
const agentEventSource = ref<EventSource | null>(null)

let alertCounter = 0

async function fetchAgents() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/agents`)
    const data = await res.json()
    agents.value = data.agents || []
  } catch (e) {
    console.error('Failed to fetch agents:', e)
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  const msg = inputMessage.value.trim()
  if (!msg || sending.value) return

  sending.value = true
  try {
    const res = await fetch(`${API_BASE}/api/agents/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    })
    const data = await res.json()
    console.log('Task dispatched:', data)
    inputMessage.value = ''
  } catch (e) {
    console.error('Failed to invoke agent:', e)
  } finally {
    sending.value = false
  }
}

function connectAgentSSE() {
  if (agentEventSource.value) {
    agentEventSource.value.close()
  }

  agentEventSource.value = new EventSource(`${API_BASE}/api/agents/events`)

  agentEventSource.value.addEventListener('agent_created', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    agents.value = agents.value.filter(a => a.id !== data.agent_id)
    agents.value.push({
      id: data.agent_id,
      name: data.agent_name,
      role: 'unknown',
      status: 'idle',
      event_count: 0,
      created_at: new Date().toISOString(),
    })
    agentLogs.value[data.agent_id] = []
  })

  agentEventSource.value.addEventListener('agent_status', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    const agent = agents.value.find(a => a.id === data.agent_id)
    if (agent) {
      agent.status = data.status
      agent.status_message = data.message
    }
    pushLog(data.agent_id, {
      id: crypto.randomUUID(),
      type: 'status',
      text: `[${data.status}] ${data.message || ''}`,
      time: new Date().toLocaleTimeString(),
    })
  })

  agentEventSource.value.addEventListener('agent_output', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    pushLog(data.agent_id, {
      id: crypto.randomUUID(),
      type: 'output',
      text: data.delta || '',
      time: new Date().toLocaleTimeString(),
    })
  })

  agentEventSource.value.addEventListener('agent_handoff', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    pushLog(data.agent_id, {
      id: crypto.randomUUID(),
      type: 'handoff',
      text: `→ ${data.from_agent} → ${data.to_agent}`,
      time: new Date().toLocaleTimeString(),
    })
  })

  agentEventSource.value.addEventListener('agent_error', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    const agent = agents.value.find(a => a.id === data.agent_id)
    if (agent) {
      agent.status = 'error'
      agent.last_error = data.error
    }
    pushLog(data.agent_id, {
      id: crypto.randomUUID(),
      type: 'error',
      text: `ERROR: ${data.error}`,
      time: new Date().toLocaleTimeString(),
    })
  })

  agentEventSource.value.addEventListener('agent_complete', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    const agent = agents.value.find(a => a.id === data.agent_id)
    if (agent) {
      agent.status = 'idle'
      if (data.result) {
        pushLog(data.agent_id, {
          id: crypto.randomUUID(),
          type: 'output',
          text: `Done: ${data.result.slice(0, 100)}`,
          time: new Date().toLocaleTimeString(),
        })
      }
    }
  })

  agentEventSource.value.addEventListener('hermes_alert', (e: MessageEvent) => {
    const data = JSON.parse(e.data)
    alerts.value.push({
      id: `alert-${++alertCounter}`,
      level: data.hermes_level || 'info',
      message: data.message,
      time: new Date().toLocaleTimeString(),
      session_id: data.session_id,
    })
    // Keep last 20 alerts
    if (alerts.value.length > 20) {
      alerts.value = alerts.value.slice(-20)
    }
  })

  agentEventSource.value.onerror = () => {
    console.log('Agent SSE connection error, will reconnect...')
  }
}

function pushLog(agentId: string, log: AgentLog) {
  if (!agentLogs.value[agentId]) {
    agentLogs.value[agentId] = []
  }
  agentLogs.value[agentId].push(log)
  if (agentLogs.value[agentId].length > 50) {
    agentLogs.value[agentId] = agentLogs.value[agentId].slice(-50)
  }
}

onMounted(async () => {
  await fetchAgents()
  connectAgentSSE()
})

onUnmounted(() => {
  if (agentEventSource.value) {
    agentEventSource.value.close()
  }
})
</script>

<style scoped>
.agent-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-title {
  font-size: 18px;
  font-weight: 600;
}

.btn-refresh {
  padding: 6px 14px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
}

.btn-refresh:hover { background: var(--hover-bg, #f5f5f5); }

.agent-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.agent-card {
  border: 1px solid var(--border-color, #ddd);
  border-radius: 8px;
  padding: 14px;
  background: var(--bg-secondary, #fafafa);
  transition: border-color 0.2s;
}

.agent-card.status-running {
  border-color: var(--color-primary, #4a9eff);
  background: color-mix(in srgb, var(--color-primary, #4a9eff) 5%, white);
}

.agent-card.status-error {
  border-color: var(--color-error, #e53935);
  background: color-mix(in srgb, var(--color-error, #e53935) 5%, white);
}

.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.agent-name {
  font-weight: 600;
  font-size: 14px;
}

.agent-status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  font-weight: 600;
}

.status-dot-sm {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.agent-status-badge.idle { background: #e8f5e9; color: #2e7d32; }
.agent-status-badge.running { background: #e3f2fd; color: #1565c0; }
.agent-status-badge.error { background: #ffebee; color: #c62828; }
.agent-status-badge.done { background: #f3e5f5; color: #6a1b9a; }

.agent-card-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.meta-item {
  display: flex;
  gap: 6px;
}

.meta-label { color: var(--text-secondary, #888); }
.meta-value { font-family: monospace; }
.meta-value.error { color: var(--color-error, #e53935); }

.agent-logs {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color, #eee);
  font-family: monospace;
  font-size: 11px;
  max-height: 100px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-log-line { color: var(--text-secondary, #666); }
.agent-log-line.output { color: var(--text-primary, #333); }
.agent-log-line.handoff { color: var(--color-primary, #4a9eff); }
.agent-log-line.error { color: var(--color-error, #e53935); }

.agent-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary, #888);
  grid-column: 1 / -1;
}

.alerts-section {
  border: 1px solid var(--border-color, #ddd);
  border-radius: 8px;
  padding: 12px;
  background: #fff8e1;
}

.alerts-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 13px;
}

.alert-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px solid #ffe082;
}

.alert-item:last-child { border-bottom: none; }

.alert-time { color: #888; font-family: monospace; font-size: 11px; }
.alert-msg { color: #333; }
.alert-item.error .alert-msg { color: #c62828; }
.alert-item.warning .alert-msg { color: #e65100; }

.agent-input-section {
  border: 1px solid var(--border-color, #ddd);
  border-radius: 8px;
  padding: 12px;
}

.input-label {
  font-size: 13px;
  margin-bottom: 8px;
  font-weight: 500;
}

.input-row {
  display: flex;
  gap: 8px;
}

.agent-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
}

.agent-input:focus {
  border-color: var(--color-primary, #4a9eff);
}

.btn-send {
  padding: 8px 20px;
  background: var(--color-primary, #4a9eff);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
