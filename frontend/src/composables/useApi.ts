// Unified fetch wrapper for all API calls

import { API_BASE } from '../config'

const defaultHeaders: Record<string, string> = { 'X-User-Role': 'operator' }

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`
  const mergedInit: RequestInit = {
    ...init,
    headers: { ...defaultHeaders, ...init?.headers },
  }
  const res = await fetch(fullUrl, mergedInit)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw { status: res.status, detail: text || res.statusText }
  }
  return res.json()
}

export function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  return request<T>(url, init)
}

export function fetchOptional<T>(url: string, init?: RequestInit): Promise<T | null> {
  return request<T>(url, init).catch(() => null)
}

export async function fetchPost<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function fetchPut<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function fetchPatch<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function fetchDelete<T = { ok: boolean }>(url: string): Promise<T> {
  return request<T>(url, { method: 'DELETE' })
}

/**
 * Extract a human-readable error message from a caught value.
 * Handles: Error instances, { status, detail } from useApi, and unknown values.
 */
export function extractError(e: unknown): string {
  if (e instanceof Error) return e.message
  if (e && typeof e === 'object' && 'detail' in e) {
    const obj = e as { status?: number; detail: string }
    try {
      const parsed = JSON.parse(obj.detail)
      if (parsed.detail) return `${obj.status ?? ''}: ${parsed.detail}`.replace(/^: /, '')
    } catch { /* not JSON */ }
    return `${obj.status ?? ''}: ${obj.detail}`.replace(/^: /, '')
  }
  return String(e ?? 'Unknown error')
}
