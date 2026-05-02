// Typed API client for v1.1 Tool Governance endpoints

import { fetchJSON, fetchPost } from './useApi'
import { API_BASE } from '../config'
import type {
  ApprovalItem,
  ApprovalListResponse,
  BatchApprovalResponse,
  ToolPolicyListResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Approvals
// ---------------------------------------------------------------------------

export function listApprovals(params?: {
  status?: string
  run_id?: string
  limit?: number
  offset?: number
  cursor?: string
}): Promise<ApprovalListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.run_id) searchParams.set('run_id', params.run_id)
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  if (params?.cursor) searchParams.set('cursor', params.cursor)
  const qs = searchParams.toString()
  return fetchJSON<ApprovalListResponse>(`${API_BASE}/api/approvals${qs ? `?${qs}` : ''}`)
}

export function approveApproval(
  approvalId: string,
  body?: { resolved_by?: string; note?: string },
): Promise<ApprovalItem> {
  return fetchPost<ApprovalItem>(
    `${API_BASE}/api/approvals/${encodeURIComponent(approvalId)}/approve`,
    body ?? {},
  )
}

export function rejectApproval(
  approvalId: string,
  body?: { resolved_by?: string; note?: string },
): Promise<ApprovalItem> {
  return fetchPost<ApprovalItem>(
    `${API_BASE}/api/approvals/${encodeURIComponent(approvalId)}/reject`,
    body ?? {},
  )
}

// ---------------------------------------------------------------------------
// Tool Policies
// ---------------------------------------------------------------------------

export function listToolPolicies(): Promise<ToolPolicyListResponse> {
  return fetchJSON<ToolPolicyListResponse>(`${API_BASE}/api/tools`)
}

// ---------------------------------------------------------------------------
// Batch Approvals (OPT-55)
// ---------------------------------------------------------------------------

export function batchApprove(
  approvalIds: string[],
  body?: { resolved_by?: string; note?: string },
): Promise<BatchApprovalResponse> {
  return fetchPost<BatchApprovalResponse>(
    `${API_BASE}/api/approvals/batch/approve`,
    { approval_ids: approvalIds, ...body },
  )
}

export function batchReject(
  approvalIds: string[],
  body?: { resolved_by?: string; note?: string },
): Promise<BatchApprovalResponse> {
  return fetchPost<BatchApprovalResponse>(
    `${API_BASE}/api/approvals/batch/reject`,
    { approval_ids: approvalIds, ...body },
  )
}
