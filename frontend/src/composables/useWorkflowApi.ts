// Typed API client for v1.0 Workflow Observability endpoints

import { fetchJSON, fetchPost, fetchPatch } from './useApi'
import { API_BASE } from '../config'
import type {
  WorkflowRuntime,
  WorkflowRun,
  WorkflowSpan,
  WorkflowRunListResponse,
  WorkflowTraceResponse,
  ConnectorListResponse,
  FailedEventListResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Runtimes
// ---------------------------------------------------------------------------

export function listRuntimes(status?: string): Promise<WorkflowRuntime[]> {
  const params = status ? `?status=${encodeURIComponent(status)}` : ''
  return fetchJSON<WorkflowRuntime[]>(`${API_BASE}/api/runtimes${params}`)
}

export function createRuntime(body: {
  name: string
  type?: string
  status?: string
  config_json?: Record<string, unknown>
}): Promise<WorkflowRuntime> {
  return fetchPost<WorkflowRuntime>(`${API_BASE}/api/runtimes`, body)
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export function listRuns(params?: {
  runtime_id?: string
  status?: string
  limit?: number
  offset?: number
}): Promise<WorkflowRunListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.runtime_id) searchParams.set('runtime_id', params.runtime_id)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<WorkflowRunListResponse>(`${API_BASE}/api/runs${qs ? `?${qs}` : ''}`)
}

export function getRun(runId: string): Promise<WorkflowRun> {
  return fetchJSON<WorkflowRun>(`${API_BASE}/api/runs/${encodeURIComponent(runId)}`)
}

export function createRun(body: {
  runtime_id: string
  title: string
  input_summary?: string
  status?: string
  metadata_json?: Record<string, unknown>
}): Promise<WorkflowRun> {
  return fetchPost<WorkflowRun>(`${API_BASE}/api/runs`, body)
}

export function updateRun(
  runId: string,
  body: {
    title?: string
    status?: string
    output_summary?: string
    error_summary?: string
    metadata_json?: Record<string, unknown>
  },
): Promise<WorkflowRun> {
  return fetchPatch<WorkflowRun>(`${API_BASE}/api/runs/${encodeURIComponent(runId)}`, body)
}

// ---------------------------------------------------------------------------
// Spans
// ---------------------------------------------------------------------------

export function createSpan(
  runId: string,
  body: {
    span_type: string
    title: string
    status?: string
    parent_span_id?: string
    agent_name?: string
    model_name?: string
    tool_name?: string
    input_summary?: string
    output_summary?: string
    error_summary?: string
    input_tokens?: number
    output_tokens?: number
    cost?: number
    metadata_json?: Record<string, unknown>
  },
): Promise<WorkflowSpan> {
  return fetchPost<WorkflowSpan>(
    `${API_BASE}/api/runs/${encodeURIComponent(runId)}/spans`,
    body,
  )
}

// ---------------------------------------------------------------------------
// Trace (run + spans)
// ---------------------------------------------------------------------------

export function getTrace(runId: string): Promise<WorkflowTraceResponse> {
  return fetchJSON<WorkflowTraceResponse>(
    `${API_BASE}/api/runs/${encodeURIComponent(runId)}/trace`,
  )
}

// ---------------------------------------------------------------------------
// Connectors
// ---------------------------------------------------------------------------

export function listConnectors(runtimeId?: string): Promise<ConnectorListResponse> {
  const params = runtimeId ? `?runtime_id=${encodeURIComponent(runtimeId)}` : ''
  return fetchJSON<ConnectorListResponse>(`${API_BASE}/api/connectors${params}`)
}

// ---------------------------------------------------------------------------
// Failed Events (OPT-54)
// ---------------------------------------------------------------------------

export function listFailedEvents(
  connectorId: string,
  params?: { limit?: number; offset?: number },
): Promise<FailedEventListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<FailedEventListResponse>(
    `${API_BASE}/api/connectors/${encodeURIComponent(connectorId)}/failed-events${qs ? `?${qs}` : ''}`,
  )
}

export function replayFailedEvent(
  connectorId: string,
  eventId: string,
): Promise<{ status: string }> {
  return fetchPost<{ status: string }>(
    `${API_BASE}/api/connectors/${encodeURIComponent(connectorId)}/failed-events/${encodeURIComponent(eventId)}/replay`,
    {},
  )
}
