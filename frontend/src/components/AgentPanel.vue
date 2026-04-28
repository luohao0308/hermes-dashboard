<template>
  <div class="agent-panel">
    <!-- Header -->
    <div class="agent-header">
      <div class="agent-title">🤖 Agent 配置</div>
      <div class="agent-actions">
        <button class="btn-secondary" @click="fetchConfig" :disabled="loading">
          刷新
        </button>
      </div>
    </div>

    <!-- Main Agent Selector -->
    <div class="config-section">
      <div class="section-label">主 Agent</div>
      <div class="section-hint">用户消息的默认入口 Agent</div>
      <select v-model="config.main_agent" class="select-main" @change="saveConfig">
        <option v-for="agent in enabledAgents" :key="agent.id" :value="agent.id">
          {{ agent.name }} ({{ agent.description }})
        </option>
      </select>
    </div>

    <!-- Handoff Topology -->
    <div class="config-section">
      <div class="section-label">Handoff 拓扑</div>
      <div class="section-hint">展示启用 Agent 之间允许的交接路径</div>
      <div class="topology-grid">
        <div
          v-for="agent in config.agents"
          :key="`topology-${agent.id}`"
          class="topology-node"
          :class="{ disabled: !agent.enabled, main: agent.id === config.main_agent }"
        >
          <div class="topology-node-head">
            <strong>{{ agent.name }}</strong>
            <span>{{ agent.id === config.main_agent ? '入口' : agent.enabled ? '启用' : '禁用' }}</span>
          </div>
          <div class="handoff-list">
            <template v-if="agent.handoffs?.length">
              <span
                v-for="target in agent.handoffs"
                :key="`${agent.id}-${target}`"
                class="handoff-chip"
                :class="{ muted: !isHandoffTargetEnabled(target) }"
              >
                → {{ target }}
              </span>
            </template>
            <span v-else class="handoff-empty">无交接目标</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Cards Grid -->
    <div class="config-section">
      <div class="section-label">可选 Agent</div>
      <div class="agent-cards-grid">
        <div
          v-for="agent in config.agents"
          :key="agent.id"
          class="agent-card"
          :class="{ disabled: !agent.enabled }"
        >
          <div class="card-toggle">
            <label class="toggle">
              <input type="checkbox" v-model="agent.enabled" @change="saveConfig" />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="card-body">
            <div class="card-name">{{ agent.name }}</div>
            <div class="card-desc">{{ agent.description }}</div>
            <div class="card-skill">Skill: {{ agent.skill || '无' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Custom Agent -->
    <div class="config-section">
      <div class="section-label">新建自定义 Agent</div>
      <div class="create-form">
        <input
          v-model="newAgent.name"
          class="form-input"
          placeholder="Agent 名称"
        />
        <input
          v-model="newAgent.description"
          class="form-input"
          placeholder="简短描述"
        />
        <textarea
          v-model="newAgent.instructions"
          class="form-textarea"
          placeholder="Agent 指令（可选，覆盖默认指令）"
          rows="3"
        ></textarea>
        <button
          class="btn-primary"
          @click="createAgent"
          :disabled="!newAgent.name.trim() || saving"
        >
          {{ saving ? '创建中...' : '创建 Agent' }}
        </button>
      </div>
    </div>

    <!-- Status -->
    <div class="status-bar">
      <span v-if="lastSaved" class="status-ok">✓ 配置已保存</span>
      <span v-if="saveError" class="status-err">✗ {{ saveError }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { API_BASE } from '../config'

interface AgentConfig {
  id: string
  name: string
  description: string
  instructions?: string
  skill?: string
  handoffs?: string[]
  enabled: boolean
  is_custom?: boolean
}

interface Config {
  main_agent: string
  agents: AgentConfig[]
}

const config = ref<Config>({ main_agent: 'dispatcher', agents: [] })
const loading = ref(false)
const saving = ref(false)
const lastSaved = ref(false)
const saveError = ref('')

const enabledAgents = computed(() =>
  config.value.agents.filter(a => a.enabled)
)

async function fetchConfig() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/agent/config`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    // Transform dict of agents to array format
    const agentsArray = Object.entries(data.agents || {}).map(([id, cfg]: [string, any]) => ({
      id,
      name: cfg.name,
      description: cfg.description,
      instructions: cfg.instructions,
      handoffs: cfg.handoffs || [],
      enabled: cfg.enabled,
      is_custom: false,
    }))
    // Include custom agents too
    const customArray = (data.custom_agents || []).map((ca: any) => ({
      id: ca.name.toLowerCase().replace(/ /g, '_'),
      name: ca.name,
      description: ca.description,
      instructions: ca.instructions,
      handoffs: ca.handoffs || [],
      enabled: ca.enabled,
      is_custom: true,
    }))
    config.value = {
      main_agent: data.main_agent || 'dispatcher',
      agents: [...agentsArray, ...customArray],
    }
  } catch (e) {
    console.error('Failed to fetch agent config:', e)
    saveError.value = '加载配置失败'
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  lastSaved.value = false
  saveError.value = ''
  try {
    // Save main agent
    await Promise.all([
      fetch(`${API_BASE}/api/agent/config/main`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ main_agent: config.value.main_agent }),
      }),
      ...config.value.agents.map(agent =>
        fetch(`${API_BASE}/api/agent/config/enabled?name=${agent.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: agent.enabled }),
        })
      ),
    ])
    lastSaved.value = true
    setTimeout(() => { lastSaved.value = false }, 2000)
  } catch (e) {
    console.error('Failed to save agent config:', e)
    saveError.value = '保存失败'
  } finally {
    saving.value = false
  }
}

function isHandoffTargetEnabled(target: string): boolean {
  const normalized = target.toLowerCase().replace(/ /g, '_')
  return config.value.agents.some(agent =>
    agent.enabled &&
    (agent.id === normalized || agent.name.toLowerCase() === target.toLowerCase())
  )
}

const newAgent = ref({
  name: '',
  description: '',
  instructions: '',
})

async function createAgent() {
  if (!newAgent.value.name.trim()) return
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/agent/config/custom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newAgent.value.name,
        description: newAgent.value.description,
        instructions: newAgent.value.instructions,
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await fetchConfig()
    newAgent.value = { name: '', description: '', instructions: '' }
  } catch (e) {
    console.error('Failed to create agent:', e)
    saveError.value = '创建失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.agent-panel {
  padding: 24px;
  max-width: 900px;
}

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.agent-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.config-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.section-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.select-main {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

.topology-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.topology-node {
  min-height: 118px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
}

.topology-node.main {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 1px var(--accent-soft);
}

.topology-node.disabled {
  opacity: 0.48;
}

.topology-node-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.topology-node-head strong {
  color: var(--text-primary);
  font-size: 13px;
}

.topology-node-head span {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--bg-primary);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
}

.handoff-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.handoff-chip,
.handoff-empty {
  padding: 5px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.handoff-chip.muted {
  opacity: 0.45;
}

.handoff-empty {
  color: var(--text-muted);
  font-weight: 500;
}

.agent-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.agent-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  transition: opacity 0.2s;
}

.agent-card.disabled {
  opacity: 0.5;
}

.card-toggle {
  flex-shrink: 0;
  padding-top: 2px;
}

.toggle {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-primary);
  border-radius: 20px;
  transition: 0.2s;
}

.toggle-slider:before {
  position: absolute;
  content: '';
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.2s;
}

.toggle input:checked + .toggle-slider {
  background: var(--color-success, #22c55e);
}

.toggle input:checked + .toggle-slider:before {
  transform: translateX(16px);
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-skill {
  font-size: 11px;
  color: var(--text-muted);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-input,
.form-textarea {
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--text-muted);
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-accent, #6366f1);
}

.form-textarea {
  resize: vertical;
}

.btn-secondary {
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  padding: 10px 20px;
  background: var(--gradient-prism);
  border: none;
  border-radius: var(--radius-pill);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  align-self: flex-start;
  box-shadow: var(--shadow-glow);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow), 0 4px 12px rgba(124, 92, 191, 0.2);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.status-bar {
  height: 24px;
  font-size: 13px;
}

.status-ok {
  color: var(--color-success, #22c55e);
}

.status-err {
  color: var(--color-error, #ef4444);
}
</style>
