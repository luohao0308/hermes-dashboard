<template>
  <div class="terminal-container" ref="containerRef">
    <div class="terminal-header">
      <span class="terminal-title">Terminal</span>
      <button class="terminal-btn" @click="clearTerminal">清空</button>
    </div>
    <div class="terminal-body" ref="terminalRef"></div>
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
  connectWebSocket()

  window.addEventListener('resize', handleResize)
}

function connectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }

  // Use sessionId from parent prop (App.vue tab management)
  // Fall back to random if not provided (e.g., direct mount without prop)
  const sid = props.sessionId || Math.random().toString(36).substring(2, 10)
  const url = buildWsUrl(sid)

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      // No artificial messages — let PTY output speak for itself
    }

    ws.onmessage = (event) => {
      const data: string = event.data
      term?.write(data)
    }

    ws.onclose = () => {
      term?.writeln('\r\n\x1b[33m! 连接已断开，正在重连...\x1b[0m')
      setTimeout(connectWebSocket, 3000)
    }

    ws.onerror = () => {
      term?.writeln('\x1b[31m✗ WebSocket 连接错误\x1b[0m')
    }

    // Send user input to server — raw mode, PTY handles echo.
    // Cooked mode \r\n from xterm.js Enter → send only \r to PTY.
    term?.onData((data) => {
      if (ws?.readyState !== WebSocket.OPEN) return
      const payload = data === '\r\n' ? '\r' : data
      ws.send(payload)
    })
  } catch (err) {
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
  // Don't close WebSocket — let session persist for reconnects
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
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.terminal-title {
  font-size: 12px;
  color: #666666;
  font-weight: 500;
}

.terminal-btn {
  padding: 2px 8px;
  font-size: 11px;
  background: #e0e0e0;
  color: #666666;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.terminal-btn:hover {
  background: #d0d0d0;
}

.terminal-body {
  flex: 1;
  padding: 0;
  background: #ffffff;
  overflow: hidden;
}

.terminal-body :deep(.xterm) {
  height: 100%;
}

.terminal-body :deep(.xterm-viewport) {
  overflow-y: auto;
}

.terminal-input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #252526;
  border-top: 1px solid #3c3c3c;
}

.terminal-prompt {
  color: #d4d4d4;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  flex-shrink: 0;
}

.terminal-input {
  flex: 1;
  background: #3c3c3c;
  color: #d4d4d4;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
  padding: 4px 10px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  outline: none;
}

.terminal-input:focus {
  border-color: #007acc;
  outline: none;
}

.terminal-input::placeholder {
  color: #6e6e6e;
}

.terminal-send-btn {
  padding: 4px 14px;
  font-size: 12px;
  background: #007acc;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
}

.terminal-send-btn:hover {
  background: #0098ff;
}
</style>
