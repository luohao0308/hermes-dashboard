// Typed API client for Audit Log endpoints

import { fetchJSON } from './useApi'
import { API_BASE } from '../config'

export interface AuditLogEntry {
  id: string
  actor_type: string | null
  actor_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  summary: string | null
  created_at: string
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[]
  total: number
  next_cursor?: string | null
  has_more: boolean
}

export function listAuditLogs(params?: {
  actor_type?: string
  actor_id?: string
  action?: string
  resource_type?: string
  resource_id?: string
  limit?: number
  offset?: number
  cursor?: string
}): Promise<AuditLogListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.actor_type) searchParams.set('actor_type', params.actor_type)
  if (params?.actor_id) searchParams.set('actor_id', params.actor_id)
  if (params?.action) searchParams.set('action', params.action)
  if (params?.resource_type) searchParams.set('resource_type', params.resource_type)
  if (params?.resource_id) searchParams.set('resource_id', params.resource_id)
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  if (params?.cursor) searchParams.set('cursor', params.cursor)
  const qs = searchParams.toString()
  return fetchJSON<AuditLogListResponse>(`${API_BASE}/api/audit-logs${qs ? `?${qs}` : ''}`)
}
