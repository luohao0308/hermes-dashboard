/**
 * Saved filters composable — OPT-51.
 *
 * Persists filter state to localStorage keyed by page namespace.
 * Does NOT persist sensitive fields (tokens, secrets, passwords).
 */

import { ref, type Ref } from 'vue'

const STORAGE_PREFIX = 'ai-control-plane:filters:'

const SENSITIVE_KEYS = new Set([
  'token', 'secret', 'password', 'api_key', 'authorization',
  'service_token', 'bearer', 'jwt',
])

function isSensitive(key: string): boolean {
  const lower = key.toLowerCase()
  return SENSITIVE_KEYS.has(lower) || lower.includes('token') || lower.includes('secret')
}

function sanitizeFilters(filters: Record<string, unknown>): Record<string, unknown> {
  const clean: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(filters)) {
    if (!isSensitive(key)) {
      clean[key] = value
    }
  }
  return clean
}

export function useSavedFilters<T extends Record<string, unknown>>(
  namespace: string,
  defaults: T,
): {
  filters: Ref<T>
  save: () => void
  clear: () => void
  hasSaved: Ref<boolean>
} {
  const storageKey = `${STORAGE_PREFIX}${namespace}`

  function loadFromStorage(): T {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<T>
        return { ...defaults, ...parsed }
      }
    } catch {
      // corrupted storage, ignore
    }
    return { ...defaults }
  }

  const filters = ref<T>(loadFromStorage()) as Ref<T>
  const hasSaved = ref(!!localStorage.getItem(storageKey))

  function save(): void {
    const sanitized = sanitizeFilters(filters.value as Record<string, unknown>)
    localStorage.setItem(storageKey, JSON.stringify(sanitized))
    hasSaved.value = true
  }

  function clear(): void {
    localStorage.removeItem(storageKey)
    filters.value = { ...defaults }
    hasSaved.value = false
  }

  return { filters, save, clear, hasSaved }
}
