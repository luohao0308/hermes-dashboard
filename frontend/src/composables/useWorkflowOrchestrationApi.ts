// Typed API client for v2.0 Workflow Orchestration endpoints

import { fetchJSON, fetchPost, fetchPut, fetchDelete } from './useApi'
import { API_BASE } from '../config'
import type {
  WorkflowDefinition,
  WorkflowDefinitionListResponse,
  WorkflowRunDetail,
  WorkflowRunDetailListResponse,
  WorkflowVersionListResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Workflow Definitions
// ---------------------------------------------------------------------------

export function listWorkflowDefinitions(params?: {
  runtime_id?: string
  limit?: number
  offset?: number
}): Promise<WorkflowDefinitionListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.runtime_id) searchParams.set('runtime_id', params.runtime_id)
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<WorkflowDefinitionListResponse>(
    `${API_BASE}/api/workflows${qs ? `?${qs}` : ''}`,
  )
}

export function getWorkflowDefinition(workflowId: string): Promise<WorkflowDefinition> {
  return fetchJSON<WorkflowDefinition>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}`,
  )
}

export function createWorkflowDefinition(body: {
  name: string
  runtime_id: string
  description?: string
  nodes: {
    node_id: string
    title: string
    task_type?: string
    config?: Record<string, unknown>
    retry_policy?: { max_retries: number; backoff_seconds: number }
    timeout_seconds?: number
  }[]
  edges?: { from_node: string; to_node: string }[]
}): Promise<WorkflowDefinition> {
  return fetchPost<WorkflowDefinition>(`${API_BASE}/api/workflows`, body)
}

export function updateWorkflowDefinition(
  workflowId: string,
  body: {
    name?: string
    description?: string
    nodes?: {
      node_id: string
      title: string
      task_type?: string
      config?: Record<string, unknown>
      retry_policy?: { max_retries: number; backoff_seconds: number }
      timeout_seconds?: number
    }[]
    edges?: { from_node: string; to_node: string }[]
  },
): Promise<WorkflowDefinition> {
  return fetchPut<WorkflowDefinition>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}`,
    body,
  )
}

export function deleteWorkflowDefinition(workflowId: string): Promise<void> {
  return fetchDelete<void>(`${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}`)
}

// ---------------------------------------------------------------------------
// Workflow Runs
// ---------------------------------------------------------------------------

export function listWorkflowRuns(
  workflowId: string,
  params?: { limit?: number; offset?: number },
): Promise<WorkflowRunDetailListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<WorkflowRunDetailListResponse>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs${qs ? `?${qs}` : ''}`,
  )
}

export function getWorkflowRun(
  workflowId: string,
  runId: string,
): Promise<WorkflowRunDetail> {
  return fetchJSON<WorkflowRunDetail>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs/${encodeURIComponent(runId)}`,
  )
}

export function startWorkflowRun(
  workflowId: string,
  body?: { input_summary?: string; metadata_json?: Record<string, unknown> },
): Promise<WorkflowRunDetail> {
  return fetchPost<WorkflowRunDetail>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs`,
    body ?? {},
  )
}

export function advanceWorkflowRun(
  workflowId: string,
  runId: string,
): Promise<WorkflowRunDetail> {
  return fetchPost<WorkflowRunDetail>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs/${encodeURIComponent(runId)}/advance`,
    {},
  )
}

export function completeWorkflowTask(
  workflowId: string,
  runId: string,
  taskId: string,
  body?: { output_summary?: string; metadata_json?: Record<string, unknown> },
): Promise<WorkflowRunDetail> {
  return fetchPost<WorkflowRunDetail>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}/complete`,
    body ?? {},
  )
}

export function failWorkflowTask(
  workflowId: string,
  runId: string,
  taskId: string,
  body?: { error_summary?: string },
): Promise<WorkflowRunDetail> {
  return fetchPost<WorkflowRunDetail>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}/fail`,
    body ?? {},
  )
}

// ---------------------------------------------------------------------------
// Workflow Version History (OPT-52)
// ---------------------------------------------------------------------------

export function listWorkflowVersions(
  workflowId: string,
): Promise<WorkflowVersionListResponse> {
  return fetchJSON<WorkflowVersionListResponse>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/versions`,
  )
}

export function rollbackWorkflow(
  workflowId: string,
  body: { version: number },
): Promise<WorkflowDefinition> {
  return fetchPost<WorkflowDefinition>(
    `${API_BASE}/api/workflows/${encodeURIComponent(workflowId)}/rollback`,
    body,
  )
}
