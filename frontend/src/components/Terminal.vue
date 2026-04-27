<template>
  <div class="terminal-container" ref="containerRef">
    <div class="terminal-header">
      <span class="terminal-title">Terminal</span>
      <div class="terminal-status">
        <span v-if="connState === 'connecting'" class="status-dot connecting"></span>
        <span v-else-if="connState === 'connected'" class="status-dot connected"></span>
        <span v-else-if="connState === 'error'" class="status-dot error"></span>
        <span v-else class="status-dot"></span>
      </div>
      <button class="terminal-btn" @click="clearTerminal">清空</button>
    </div>
    <div class="terminal-body" ref="terminalRef">
      <!-- xterm renders into terminalRef, overlay sits on top when loading -->
      <div v-if="connState === 'connecting'" class="terminal-loading">
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
  sessionId?: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const terminalRef = ref<HTMLElement | null>(null)

// Connection state: idle → connecting → connected → disconnected/error
const connState = ref<'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'>('idle')

let term: XTerm | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

// Message buffer: accumulates WS data before xterm is ready
const msgBuffer: string[] = []
let xtermReady = false

const BASE_WS_URL = `ws://localhost:8000/ws/terminal`

function buildWsUrl(sid: string): string {
  return `${BASE_WS_URL}?session_id=${sid}`
}

function flushBuffer() {
  if (!term || !xtermReady) return
  if (msgBuffer.length === 0) return
  // Write all buffered data at once (preserves terminal state)
  const all = msgBuffer.splice(0)
  for (const chunk of all) {
    term.write(chunk)
  }
}

function initTerminal() {
  if (!terminalRef.value) {
    console.error('[Terminal] terminalRef not available')
    return
  }

  term = new XTerm({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#000000',
      foreground: '#ffffff',
      cursor: '#ffffff',
      selectionBackground: '#264f78',
      black: '#000000',
      brightBlack: '#555555',
      red: '#ff5555',
      brightRed: '#ff6e6e',
      green: '#50fa7b',
      brightGreen: '#69ff94',
      yellow: '#f1fa8c',
      brightYellow: '#ffffa5',
      blue: '#6272a4',
      brightBlue: '#8be9fd',
      magenta: '#ff79c6',
      brightMagenta: '#ff92df',
      cyan: '#8be9fd',
      brightCyan: '#a4ffff',
      white: '#f8f8f2',
      brightWhite: '#ffffff'
    },
    rows: 24,
    cols: 80,
    convertEol: true
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)

  // Mark xterm ready before open — buffering starts immediately
  xtermReady = true

  // Open terminal into DOM
  term.open(terminalRef.value)

  // Flush any buffered messages that arrived before xterm was ready
  flushBuffer()

  // Wait for DOM to paint, then fit
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      try {
        fitAddon?.fit()
        console.log('[Terminal] xterm fitted, rows:', term?.rows, 'cols:', term?.cols)
      } catch (e) {
        console.error('[Terminal] fit error:', e)
      }
    })
  })

  // Watch for container size changes
  resizeObserver = new ResizeObserver(() => {
    try {
      fitAddon?.fit()
    } catch (e) {
      // ignore
    }
  })
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }

  // Connect WebSocket
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
  console.log('[Terminal] Connecting to', url)

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      console.log('[Terminal] WebSocket connected')
      connState.value = 'connected'
      // Backend will send {"type":"session","status":"new"|"reconnect"}
      // We handle the replay trigger in onmessage
    }

    ws.onmessage = (event) => {
      const data: string = event.data
      // Handle session status messages from backend
      try {
        const msg = JSON.parse(data)
        if (msg.type === 'session') {
          // Backend sends {"type": "session", "status": "new"|"reconnect"}
          // PTY echo (when user types) + backend PTY output provide all terminal I/O.
          // No extra action needed here.
          return
        }
      } catch (_) {
        // Not JSON — pass through to terminal
      }
      if (term && xtermReady) {
        term.write(data)
      } else {
        // Buffer messages until xterm is ready
        msgBuffer.push(data)
      }
    }

    ws.onclose = () => {
      if (connState.value !== 'error') {
        connState.value = 'disconnected'
      }
      // Don't auto-reconnect here — component remounts on navigation,
      // which creates a fresh connection via onMounted → initTerminal()
    }

    ws.onerror = (e) => {
      console.error('[Terminal] WebSocket error', e)
      connState.value = 'error'
    }

    term?.onData((data) => {
      if (ws?.readyState !== WebSocket.OPEN) return
      const payload = data === '\r\n' ? '\r' : data
      ws.send(payload)
    })
  } catch (err) {
    console.error('[Terminal] Connection error:', err)
    connState.value = 'error'
    term?.writeln(`\x1b[31m✗ 连接失败: ${err}\x1b[0m`)
  }
}

function handleResize() {
  try {
    fitAddon?.fit()
  } catch (e) {
    // ignore
  }
}

function clearTerminal() {
  term?.clear()
}

onMounted(() => {
  // Small delay to ensure parent has laid out the container
  setTimeout(initTerminal, 100)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  ws = null
  xtermReady = false
  msgBuffer.length = 0
  term?.dispose()
  term = null
})
</script>

<style scoped>
.terminal-container {
  display: flex;
  flex-direction: column;
  background: #000000;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  overflow: hidden;
  height: calc(100vh - 140px);
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #1e1e1e;
  border-bottom: 1px solid #3c3c3c;
  flex-shrink: 0;
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
  background: #555555;
}

.status-dot.connecting {
  background: #e5a50a;
  animation: pulse 1s ease-in-out infinite;
}

.status-dot.connected {
  background: #50fa7b;
}

.status-dot.error {
  background: #ff5555;
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
  background: #000000;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

/* xterm core */
.terminal-body :deep(.xterm) {
  height: 100%;
  width: 100%;
  padding: 0;
}

.terminal-body :deep(.xterm-viewport) {
  overflow-y: auto;
}

.terminal-body :deep(.xterm-screen) {
  padding: 8px;
}

.terminal-body :deep(.xterm-helper-layer) {
  contain: strict;
}

/* Loading overlay — sits on top of xterm canvas */
.terminal-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  background: #000000;
  pointer-events: none;
}

.loading-text {
  color: #555555;
  font-size: 13px;
  font-family: Menlo, Monaco, "Courier New", monospace;
  letter-spacing: 0.02em;
}
</style>
