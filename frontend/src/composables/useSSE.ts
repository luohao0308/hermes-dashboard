// Shared SSE connection management with auto-reconnect

import { ref, onUnmounted } from 'vue'
import { API_BASE } from '../config'

const MAX_RECONNECT_ATTEMPTS = 10
const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30000

function getReconnectDelay(attempt: number): number {
  const delay = Math.min(BASE_DELAY_MS * Math.pow(2, attempt), MAX_DELAY_MS)
  return delay + Math.random() * delay * 0.2
}

type SSEEventHandler = (event: MessageEvent) => void

interface SSEOptions {
  url: string
  events: Record<string, SSEEventHandler>
  onOpen?: () => void
  onError?: (willReconnect: boolean) => void
  autoConnect?: boolean
}

export function useSSE(options: SSEOptions) {
  const isConnected = ref(false)
  const isReconnecting = ref(false)
  const reconnectAttempts = ref(0)

  let eventSource: EventSource | null = null

  function connect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    const fullUrl = options.url.startsWith('http') ? options.url : `${API_BASE}${options.url}`
    eventSource = new EventSource(fullUrl)

    for (const [eventName, handler] of Object.entries(options.events)) {
      eventSource.addEventListener(eventName, handler)
    }

    eventSource.onopen = () => {
      isConnected.value = true
      isReconnecting.value = false
      reconnectAttempts.value = 0
      options.onOpen?.()
    }

    eventSource.onerror = () => {
      isConnected.value = false
      eventSource?.close()

      if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
        options.onError?.(false)
        return
      }

      const delay = getReconnectDelay(reconnectAttempts.value)
      reconnectAttempts.value++
      isReconnecting.value = true
      options.onError?.(true)

      setTimeout(connect, delay)
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
    isReconnecting.value = false
  }

  if (options.autoConnect !== false) {
    connect()
  }

  onUnmounted(disconnect)

  return {
    isConnected,
    isReconnecting,
    reconnectAttempts,
    connect,
    disconnect,
  }
}
