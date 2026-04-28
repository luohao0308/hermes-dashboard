<template>
  <div class="agent-chat">
    <!-- Left sidebar: session list -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <button class="btn-new-chat" @click="createSession()">+ 新对话</button>
      </div>
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.session_id"
          class="session-item"
          :class="{ active: session.session_id === currentSessionId }"
          @click="selectSession(session.session_id)"
        >
          <span class="session-main">
            <span class="session-name">{{ sessionTitle(session) }}</span>
            <span v-if="session.linked_session_id" class="session-context">
              关联 #{{ session.linked_session_id.slice(0, 8) }}
            </span>
          </span>
          <button
            class="session-delete"
            @click.stop="deleteSession(session.session_id)"
            title="删除会话"
          >×</button>
        </div>
        <div v-if="sessions.length === 0" class="session-empty">
          暂无会话
        </div>
      </div>
    </aside>

    <!-- Right: chat area -->
    <main class="chat-main">
      <!-- No session selected -->
      <div v-if="!currentSessionId" class="chat-empty-state">
        <div class="empty-icon">🤖</div>
        <div class="empty-title">选择一个会话开始聊天</div>
        <div class="empty-hint">或者点击左上角「+ 新对话」新建一个</div>
      </div>

      <!-- Active chat -->
      <template v-else>
        <!-- Chat header -->
        <div class="chat-header">
          <div class="header-left">
            <select
              v-if="availableAgents.length > 0"
              class="agent-select"
              :value="currentAgentName"
              @change="switchAgent(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="agent in availableAgents" :key="agent" :value="agent">{{ AGENT_NAMES_CN[agent] || agent }}</option>
            </select>
            <span v-else class="agent-badge">{{ currentAgentName }}</span>
            <button v-if="currentLinkedSessionId" class="linked-session-chip" @click="openLinkedSession">
              关联 #{{ currentLinkedSessionId.slice(0, 8) }}
            </button>
          </div>
          <div class="header-actions">
            <button class="btn-clear" @click="clearSession" title="清空对话">清空</button>
          </div>
        </div>

        <!-- Messages -->
        <div class="messages-area" ref="messagesRef">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="`message-${msg.role}`"
          >
            <div class="message-avatar">
              <template v-if="msg.role === 'user'">👤</template>
              <template v-else>🤖</template>
            </div>
            <div class="message-content">
              <div v-if="msg.agent_name" class="message-agent-name">{{ msg.agent_name }}</div>
              <div class="message-text">{{ msg.content }}</div>
            </div>
          </div>

          <!-- Thinking indicator -->
          <div v-if="isThinking" class="message message-assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="thinking-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="input-area">
          <textarea
            v-model="inputText"
            class="chat-input"
            placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
            rows="1"
            :disabled="isThinking"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="null"
            @input="autoResize"
          ></textarea>
          <button
            v-if="isThinking"
            class="btn-stop"
            @click="stopAgent"
            title="停止"
          >
            ■
          </button>
          <button
            v-else
            class="btn-send"
            :disabled="!inputText.trim()"
            @click="sendMessage"
          >
            发送
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, nextTick, onUnmounted } from 'vue'
import { API_BASE } from '../config'

// Session types
interface ChatSession {
  session_id: string
  agent_id: string
  message_count: number
  created_at: string
  is_running: boolean
  title?: string | null
  linked_session_id?: string | null
  terminal_session_id?: string | null
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
  agent_name?: string
}

// Chinese display names for agents (used in UI)
const AGENT_NAMES_CN: Record<string, string> = {
  'Developer': '开发者',
  'DevOps': '运维',
  'Dispatcher': '调度员',
  'Researcher': '研究员',
  'Reviewer': '审查员',
  'Tester': '测试员',
}
// Reverse map: CN -> EN (for switchAgent)
const AGENT_NAMES_EN: Record<string, string> = Object.fromEntries(
  Object.entries(AGENT_NAMES_CN).map(([en, cn]) => [cn, en])
)

// Ordered list of CN names
const AGENT_ORDER_CN = ['调度员', '开发者', '运维', '研究员', '审查员', '测试员']

// State
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | null>(null)
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isThinking = ref(false)
const messagesRef = ref<HTMLElement | null>(null)
const currentAgentName = ref('Dispatcher')
const availableAgents = ref<string[]>([])
let eventSource: EventSource | null = null

const currentSession = computed(() =>
  sessions.value.find(session => session.session_id === currentSessionId.value) || null
)
const currentLinkedSessionId = computed(() => currentSession.value?.linked_session_id || '')

// Computed
function sessionTitle(session: ChatSession): string {
  if (session.title) return session.title
  const d = new Date(session.created_at)
  const date = d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  const time = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return `${date} ${time}`
}

// Actions
async function fetchSessions() {
  try {
    const res = await fetch(`${API_BASE}/api/agent/chat`)
    const data = await res.json()
    sessions.value = data.sessions || []
  } catch (e) {
    console.error('Failed to fetch sessions:', e)
  }
}

async function createSession(options: { linkedSessionId?: string; title?: string } = {}) {
  try {
    const res = await fetch(`${API_BASE}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: 'main',
        linked_session_id: options.linkedSessionId,
        title: options.title,
      }),
    })
    const data = await res.json()
    sessions.value.unshift({
      session_id: data.session_id,
      agent_id: data.agent_id,
      title: data.title,
      linked_session_id: data.linked_session_id,
      terminal_session_id: data.terminal_session_id,
      message_count: 0,
      created_at: data.created_at,
      is_running: false,
    })
    await selectSession(data.session_id)
  } catch (e) {
    console.error('Failed to create session:', e)
  }
}

async function openOrCreateLinkedSession(linkedSessionId: string, title?: string | null) {
  const existing = sessions.value.find(session => session.linked_session_id === linkedSessionId)
  if (existing) {
    await selectSession(existing.session_id)
    return
  }
  await createSession({
    linkedSessionId,
    title: title || `Hermès #${linkedSessionId.slice(0, 8)} 复盘`,
  })
  inputText.value = '请基于关联的 Hermès session 上下文，继续分析当前问题并给出下一步行动。'
}

async function selectSession(sessionId: string) {
  // Close existing SSE
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }

  currentSessionId.value = sessionId
  messages.value = []
  isThinking.value = false

  const session = sessions.value.find(s => s.session_id === sessionId)
  if (session) {
    currentAgentName.value = session.agent_id === 'main' ? 'Dispatcher' : session.agent_id
  }

  // Fetch history + open SSE stream
  await fetchHistoryAndStream(sessionId)
  // Load available agents
  fetchAgents()
}

async function fetchAgents() {
  try {
    const res = await fetch(`${API_BASE}/api/agents`)
    const data = await res.json()
    // Show Chinese names in sorted order
    availableAgents.value = (data.agents || [])
      .map((a: any) => a.name)
      .filter((name: string) => AGENT_NAMES_CN[name])
      .sort((a: string, b: string) => {
        return AGENT_ORDER_CN.indexOf(AGENT_NAMES_CN[a]) - AGENT_ORDER_CN.indexOf(AGENT_NAMES_CN[b])
      })
  } catch (e) {
    console.error('Failed to fetch agents:', e)
  }
}

async function switchAgent(agentNameCN: string) {
  if (!currentSessionId.value) return
  // Translate CN name to EN for API
  const agentNameEN = AGENT_NAMES_EN[agentNameCN] || agentNameCN
  try {
    // Stop any running agent first (PATCH fails with 409 if session is busy)
    if (isThinking.value) {
      await fetch(`${API_BASE}/api/agent/chat/${currentSessionId.value}/stop`, { method: 'POST' })
      isThinking.value = false
    }
    const res = await fetch(`${API_BASE}/api/agent/chat/${currentSessionId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentNameEN }),
    })
    if (res.ok) {
      currentAgentName.value = agentNameEN
      // Update local sessions list so selectSession uses the correct agent
      const session = sessions.value.find(s => s.session_id === currentSessionId.value)
      if (session) {
        session.agent_id = agentNameEN
      }
    } else {
      console.error('Switch agent failed:', res.status, await res.text())
    }
  } catch (e) {
    console.error('Failed to switch agent:', e)
  }
}

async function fetchHistoryAndStream(sessionId: string) {
  // Open SSE stream
  eventSource = new EventSource(`${API_BASE}/api/agent/chat/${sessionId}/stream`)

  eventSource.addEventListener('history', (e) => {
    try {
      const data = JSON.parse(e.data)
      // Deduplicate: avoid adding if last message has same content
      const last = messages.value[messages.value.length - 1]
      if (!last || last.content !== data.content || last.role !== data.role) {
        messages.value.push({
          role: data.role,
          content: data.content,
          timestamp: data.timestamp,
          agent_name: data.agent_name,
        })
        scrollToBottom()
      }
    } catch (err) {
      console.error('Failed to parse history event:', err)
    }
  })

  eventSource.addEventListener('user_message', (e) => {
    try {
      const data = JSON.parse(e.data)
      messages.value.push({ role: 'user', content: data.content, timestamp: data.timestamp })
      scrollToBottom()
    } catch (err) {
      console.error('Failed to parse user_message:', err)
    }
  })

  eventSource.addEventListener('agent_status', (e) => {
    try {
      const data = JSON.parse(e.data)
      isThinking.value = data.status === 'running'
    } catch (err) {
      console.error('Failed to parse agent_status:', err)
    }
  })

  eventSource.addEventListener('agent_output', (e) => {
    try {
      const data = JSON.parse(e.data)
      // Append delta to last assistant message, or create new one
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        last.content += data.delta || ''
        last.agent_name = data.agent_name || last.agent_name
      } else {
        messages.value.push({
          role: 'assistant',
          content: data.delta || '',
          agent_name: data.agent_name,
        })
      }
      scrollToBottom()
    } catch (err) {
      console.error('Failed to parse agent_output:', err)
    }
  })

  eventSource.addEventListener('agent_handoff', (e) => {
    try {
      const data = JSON.parse(e.data)
      currentAgentName.value = data.to_agent || currentAgentName.value
      // Add handoff indicator
      messages.value.push({
        role: 'system',
        content: `🔄 交接给 ${data.to_agent}（来自 ${data.from_agent}）`,
      })
      scrollToBottom()
    } catch (err) {
      console.error('Failed to parse agent_handoff:', err)
    }
  })

  eventSource.addEventListener('agent_tool', (e) => {
    try {
      const data = JSON.parse(e.data)
      messages.value.push({
        role: 'system',
        content: `工具事件: ${data.tool_name || data.summary || 'tool'}`,
        agent_name: data.agent_name,
      })
      scrollToBottom()
    } catch (err) {
      console.error('Failed to parse agent_tool:', err)
    }
  })

  eventSource.addEventListener('agent_complete', (e) => {
    try {
      const data = JSON.parse(e.data)
      isThinking.value = false
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant' && !last.content) {
        last.content = data.content || ''
      }
      // Update session agent name
      if (data.agent_name) {
        currentAgentName.value = data.agent_name
        const session = sessions.value.find(s => s.session_id === currentSessionId.value)
        if (session) session.agent_id = data.agent_name
      }
    } catch (err) {
      console.error('Failed to parse agent_complete:', err)
    }
  })

  eventSource.addEventListener('agent_error', (e) => {
    try {
      const data = JSON.parse(e.data)
      isThinking.value = false
      messages.value.push({
        role: 'system',
        content: `❌ 错误: ${data.error}`,
      })
      scrollToBottom()
    } catch (err) {
      console.error('Failed to parse agent_error:', err)
    }
  })

  eventSource.addEventListener('agent_stopped', (e) => {
    isThinking.value = false
    try {
      const data = JSON.parse(e.data)
      messages.value.push({
        role: 'system',
        content: `⏹ 已停止${data.message ? ': ' + data.message : ''}`,
      })
      scrollToBottom()
    } catch {}
  })

  eventSource.onerror = () => {
    // SSE disconnected — will auto-reconnect by browser if needed
    // Only show error if we have no session
    if (!currentSessionId.value) {
      console.warn('SSE stream disconnected')
    }
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isThinking.value || !currentSessionId.value) return

  inputText.value = ''
  // Reset textarea height
  const el = document.querySelector('.chat-input') as HTMLTextAreaElement
  if (el) el.style.height = 'auto'

  try {
    const res = await fetch(`${API_BASE}/api/agent/chat/${currentSessionId.value}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
    if (!res.ok) {
      const err = await res.json()
      messages.value.push({ role: 'system', content: `❌ 发送失败: ${err.detail}` })
      scrollToBottom()
    }
  } catch (e) {
    messages.value.push({ role: 'system', content: `❌ 网络错误` })
    scrollToBottom()
  }
}

async function stopAgent() {
  if (!isThinking.value || !currentSessionId.value) return
  try {
    await fetch(`${API_BASE}/api/agent/chat/${currentSessionId.value}/stop`, {
      method: 'POST',
    })
  } catch (e) {
    console.error('Failed to stop agent:', e)
  }
}

async function deleteSession(sessionId: string) {
  if (!confirm('确定删除这个会话？')) return
  try {
    await fetch(`${API_BASE}/api/agent/chat/${sessionId}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null
      messages.value = []
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    }
  } catch (e) {
    console.error('Failed to delete session:', e)
  }
}

async function clearSession() {
  if (!currentSessionId.value) return
  // Delete and recreate
  try {
    const oldId = currentSessionId.value
    await fetch(`${API_BASE}/api/agent/chat/${oldId}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter(s => s.session_id !== oldId)
    currentSessionId.value = null
    messages.value = []
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    // Create new session immediately
    await createSession()
  } catch (e) {
    console.error('Failed to clear session:', e)
  }
}

function openLinkedSession() {
  if (!currentLinkedSessionId.value) return
  window.location.hash = `#/sessions/${encodeURIComponent(currentLinkedSessionId.value)}`
}

function readLinkedSessionRequest(): { linkedSessionId: string; title?: string | null } | null {
  const [, query = ''] = window.location.hash.split('?')
  if (!query) return null
  const params = new URLSearchParams(query)
  const linkedSessionId = params.get('linked_session_id')
  if (!linkedSessionId) return null
  return {
    linkedSessionId,
    title: params.get('title'),
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

// Init
async function init() {
  await fetchSessions()
  const linkedRequest = readLinkedSessionRequest()
  if (linkedRequest) {
    await openOrCreateLinkedSession(linkedRequest.linkedSessionId, linkedRequest.title)
    return
  }
  // Auto-select last session if any
  if (sessions.value.length > 0) {
    await selectSession(sessions.value[0].session_id)
  }
}

init()

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})
</script>

<style scoped>
.agent-chat {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ---- Sidebar ---- */
.chat-sidebar {
  width: 240px;
  min-width: 240px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.btn-new-chat {
  width: 100%;
  padding: 10px 16px;
  background: var(--gradient-prism);
  color: white;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-glow);
}
.btn-new-chat:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow), 0 4px 12px rgba(124, 92, 191, 0.2);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  transition: all 0.2s ease;
}
.session-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.session-item.active {
  background: var(--accent-soft);
  color: var(--accent-color);
  font-weight: 500;
}
.session-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-main {
  flex: 1;
  min-width: 0;
}
.session-context {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-delete {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: all 0.2s ease;
}
.session-item:hover .session-delete {
  opacity: 1;
}
.session-delete:hover {
  color: var(--error-color);
}
.session-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px 0;
}

/* ---- Main ---- */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-primary);
}

.chat-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  background: var(--bg-secondary);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.empty-hint {
  font-size: 13px;
}

/* Chat header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.header-left,
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.agent-badge {
  background: var(--gradient-prism);
  color: white;
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  box-shadow: var(--shadow-glow);
}
.agent-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  min-width: 120px;
  transition: all 0.2s ease;
}
.agent-select:hover {
  border-color: var(--accent-color);
}
.agent-select:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.linked-session-chip {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent-color);
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.btn-clear {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-clear:hover {
  background: var(--error-soft);
  color: var(--error-color);
  border-color: var(--error-color);
}

/* Messages */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg-secondary);
}

.message {
  display: flex;
  gap: 12px;
  max-width: 75%;
  animation: fadeIn 0.3s ease;
}
.message-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message-assistant {
  align-self: flex-start;
}
.message-system {
  align-self: center;
  max-width: 100%;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 8px 16px;
  border-radius: var(--radius-pill);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-avatar {
  font-size: 22px;
  flex-shrink: 0;
  margin-top: 2px;
}
.message-content {
  flex: 1;
}
.message-agent-name {
  font-size: 11px;
  color: var(--accent-color);
  font-weight: 600;
  margin-bottom: 6px;
}
.message-text {
  background: var(--bg-primary);
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  border-top-left-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: var(--shadow-sm);
}
.message-user .message-text {
  background: var(--gradient-prism);
  color: white;
  border-radius: var(--radius-lg);
  border-top-right-radius: 4px;
  box-shadow: var(--shadow-glow);
}
.message-system .message-text {
  background: transparent;
  color: var(--text-muted);
  padding: 0;
  font-size: 12px;
}

/* Thinking dots */
.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.thinking-dots span {
  width: 8px;
  height: 8px;
  background: var(--accent-color);
  border-radius: 50%;
  animation: bounce 1.2s infinite;
  opacity: 0.7;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(1); opacity: 0.5; }
  40% { transform: scale(1.3); opacity: 1; }
}

/* Input area */
.input-area {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-family: var(--font-sans);
  resize: none;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  outline: none;
  transition: all 0.2s ease;
  background: var(--bg-primary);
  color: var(--text-primary);
}
.chat-input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.chat-input:disabled {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}
.chat-input::placeholder {
  color: var(--text-muted);
}

.btn-send {
  padding: 12px 24px;
  background: var(--gradient-prism);
  color: white;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
  box-shadow: var(--shadow-glow);
}
.btn-send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow), 0 4px 12px rgba(124, 92, 191, 0.2);
}
.btn-send:disabled {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
}

.btn-stop {
  padding: 12px 24px;
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.btn-stop:hover {
  background: #dc2626;
}
</style>
