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

const containerRef = ref<HTMLElement | null>(null)
const terminalRef = ref<HTMLElement | null>(null)

let term: XTerm | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

const SESSION_KEY = 'hermes_terminal_session_id'
const BASE_WS_URL = `ws://localhost:8000/ws/terminal`

function getSessionId(): string {
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = Math.random().toString(36).substring(2, 10)
    localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}

function buildWsUrl(sid: string): string {
  return `${BASE_WS_URL}?session_id=${sid}`
}

function initTerminal() {
  if (!terminalRef.value) return

  term = new XTerm({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    allowTransparency: true,
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

  term.writeln('\x1b[36mHermès Terminal\x1b[0m - 连接到终端...')
  connectWebSocket()

  window.addEventListener('resize', handleResize)
}

function connectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }

  const sid = getSessionId()
  const url = buildWsUrl(sid)

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      term?.writeln('\x1b[32m✓\x1b[0m 已连接到终端')
      term?.writeln('')
    }

    ws.onmessage = (event) => {
      const data: string = event.data

      // Server announces session id: [Session: abc123]
      if (data.startsWith('[Session:')) {
        const newSid = data.match(/\[Session: (\S+)\]/)?.[1]
        if (newSid && newSid !== sid) {
          localStorage.setItem(SESSION_KEY, newSid)
        }
        return // don't display the session announcement
      }

      // Reconnect confirmation message — display but don't treat as terminal output
      if (data.includes('✓ 会话已恢复')) {
        term?.writeln('\x1b[32m✓ 会话已恢复\x1b[0m')
        return
      }

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
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
}

.terminal-title {
  font-size: 12px;
  color: #cccccc;
  font-weight: 500;
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
  padding: 8px;
  background: #1e1e1e;
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
