<template>
  <div class="terminal-container" ref="containerRef">
    <div class="terminal-header">
      <span class="terminal-title">Terminal</span>
      <div class="terminal-status">
        <span v-if="connState === 'connecting'" class="status-dot connecting"></span>
        <span v-else-if="connState === 'connected'" class="status-dot connected"></span>
        <span v-else class="status-dot error"></span>
      </div>
      <button class="terminal-btn" @click="clearTerminal">清空</button>
    </div>
    <div class="terminal-body" ref="terminalRef">
      <div v-if="connState === 'connecting'" class="terminal-overlay">
        <span class="loading-text">正在连接终端...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const props = defineProps<{
  sessionId?: string  // session ID from parent (App.vue tab management)
}>()

const containerRef = ref<HTMLElement | null>(null)
const terminalRef = ref<HTMLElement | null>(null)

// 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'
const connState = ref<'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'>('idle')

let term: XTerm | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

const BASE_WS_URL = `ws://localhost:8000/ws/terminal`

function buildWsUrl(sid: string): string {
  return `${BASE_WS_URL}?session_id=${sid}`
}

function initTerminal() {
  if (!terminalRef.value) return

  term = new XTerm({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#d4d4d4',
      selectionBackground: '#264f78'
    },
    rows: 24
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalRef.value)
  fitAddon.fit()

  // Remove the loading overlay once xterm is rendered
  connState.value = 'connecting'
  connectWebSocket()

  window.addEventListener('resize', handleResize)
}

function connectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }

  const sid = props.sessionId || Math.random().toString(36).substring(2, 10)
  const url = buildWsUrl(sid)

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      connState.value = 'connected'
    }

    ws.onmessage = (event) => {
      const data: string = event.data
      term?.write(data)
    }

    ws.onclose = () => {
      connState.value = 'disconnected'
      term?.writeln('\r\n\x1b[33m! 连接已断开，正在重连...\x1b[0m')
      setTimeout(connectWebSocket, 3000)
    }

    ws.onerror = () => {
      connState.value = 'error'
      term?.writeln('\x1b[31m\x1b[5m✗\x1b[0m\x1b[31m WebSocket 连接错误\x1b[0m')
    }

    term?.onData((data) => {
      if (ws?.readyState !== WebSocket.OPEN) return
      const payload = data === '\r\n' ? '\r' : data
      ws.send(payload)
    })
  } catch (err) {
    connState.value = 'error'
    term?.writeln(`\x1b[31m✗ 连接失败: ${err}\x1b[0m`)
  }
}

function handleResize() {
  fitAddon?.fit()
}

function clearTerminal() {
  term?.clear()
}

onMounted(() => {
  setTimeout(initTerminal, 100)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  ws = null
  term?.dispose()
  term = null
})
</script>

<style scoped>
.terminal-container {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  height: calc(100vh - 140px);
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
}

.terminal-title {
  font-size: 12px;
  color: #cccccc;
  font-weight: 500;
}

.terminal-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 auto;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connecting {
  background: #e5a50a;
  animation: pulse 1s ease-in-out infinite;
}

.status-dot.connected {
  background: #4ec9b0;
}

.status-dot.error {
  background: #f14c4c;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.terminal-btn {
  padding: 2px 8px;
  font-size: 11px;
  background: #3c3c3c;
  color: #cccccc;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.terminal-btn:hover {
  background: #4a4a4a;
}

.terminal-body {
  flex: 1;
  padding: 0;
  background: #1e1e1e;
  overflow: hidden;
  position: relative;
}

.terminal-body :deep(.xterm) {
  height: 100%;
}

.terminal-body :deep(.xterm-viewport) {
  overflow-y: auto;
}

/* Loading overlay — centered on top of the black background */
.terminal-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e1e1e;
  z-index: 10;
  pointer-events: none;
}

.loading-text {
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #888888;
  animation: pulse 1.5s ease-in-out infinite;
}
</style>
