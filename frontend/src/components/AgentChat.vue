<template>
  <div class="agent-chat">
    <!-- Left sidebar: session list -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <button class="btn-new-chat" @click="createSession">+ 新对话</button>
      </div>
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.session_id"
          class="session-item"
          :class="{ active: session.session_id === currentSessionId }"
          @click="selectSession(session.session_id)"
        >
          <span class="session-name">{{ sessionTitle(session) }}</span>
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
          <div class="header-agent">
            <span class="agent-badge">{{ currentAgentName }}</span>
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
            class="btn-send"
            :disabled="!inputText.trim() || isThinking"
            @click="sendMessage"
          >
            {{ isThinking ? '...' : '发送' }}
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onUnmounted } from 'vue'

const API_BASE = 'http://localhost:8000'

// Session types
interface ChatSession {
  session_id: string
  agent_id: string
  message_count: number
  created_at: string
  is_running: boolean
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
  agent_name?: string
}

// State
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | null>(null)
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isThinking = ref(false)
const messagesRef = ref<HTMLElement | null>(null)
const currentAgentName = ref('Agent')
let eventSource: EventSource | null = null

// Computed
function sessionTitle(session: ChatSession): string {
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

async function createSession() {
  try {
    const res = await fetch(`${API_BASE}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: 'main' }),
    })
    const data = await res.json()
    sessions.value.unshift({
      session_id: data.session_id,
      agent_id: data.agent_id,
      message_count: 0,
      created_at: data.created_at,
      is_running: false,
    })
    await selectSession(data.session_id)
  } catch (e) {
    console.error('Failed to create session:', e)
  }
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
    currentAgentName.value = session.agent_id === 'main' ? 'Agent' : session.agent_id
  }

  // Fetch history + open SSE stream
  await fetchHistoryAndStream(sessionId)
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
  width: 220px;
  min-width: 220px;
  background: #f7f8fa;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.btn-new-chat {
  width: 100%;
  padding: 8px 12px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-new-chat:hover {
  background: #059669;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
  margin-bottom: 2px;
  transition: background 0.1s;
}
.session-item:hover {
  background: #e5e7eb;
}
.session-item.active {
  background: #d1fae5;
  color: #065f46;
  font-weight: 500;
}
.session-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-delete {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.1s;
}
.session-item:hover .session-delete {
  opacity: 1;
}
.session-delete:hover {
  color: #ef4444;
}
.session-empty {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px 0;
}

/* ---- Main ---- */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
}

.chat-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: #374151;
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
  padding: 10px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
}
.agent-badge {
  background: #10b981;
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.btn-clear {
  background: none;
  border: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-clear:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

/* Messages */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
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
  color: #9ca3af;
  background: #f9fafb;
  padding: 4px 12px;
  border-radius: 12px;
}

.message-avatar {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}
.message-content {
  flex: 1;
}
.message-agent-name {
  font-size: 11px;
  color: #10b981;
  font-weight: 500;
  margin-bottom: 4px;
}
.message-text {
  background: #f3f4f6;
  padding: 10px 14px;
  border-radius: 12px;
  border-top-left-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}
.message-user .message-text {
  background: #10b981;
  color: white;
  border-radius: 12px;
  border-top-right-radius: 4px;
}
.message-system .message-text {
  background: transparent;
  color: #9ca3af;
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
  width: 6px;
  height: 6px;
  background: #9ca3af;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
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
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fafafa;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  outline: none;
  transition: border-color 0.15s;
}
.chat-input:focus {
  border-color: #10b981;
}
.chat-input:disabled {
  background: #f3f4f6;
  color: #9ca3af;
}

.btn-send {
  padding: 10px 20px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  flex-shrink: 0;
}
.btn-send:hover:not(:disabled) {
  background: #059669;
}
.btn-send:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
</style>
