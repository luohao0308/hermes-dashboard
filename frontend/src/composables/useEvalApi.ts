// Typed API client for v1.4 Eval & Config Version endpoints

import { fetchJSON, fetchPost } from './useApi'
import { API_BASE } from '../config'
import type {
  EvalSummaryData,
  EvalResultListResponse,
  ConfigVersionItem,
  ConfigVersionListResponse,
  ConfigCompareData,
} from '../types'

interface EvalRunResponse {
  eval_run_id: string
  mode: string
  count: number
  passed: number
  failed: number
  avg_score: number
  results: Array<{
    sample_id?: string
    category?: string
    title?: string
    score: number
    passed: boolean
    findings: Array<Record<string, unknown>>
  }>
}

export function getEvalSummary(params?: {
  runtime_id?: string
  config_version?: string
  from_date?: string
  to_date?: string
}): Promise<EvalSummaryData> {
  const searchParams = new URLSearchParams()
  if (params?.runtime_id) searchParams.set('runtime_id', params.runtime_id)
  if (params?.config_version) searchParams.set('config_version', params.config_version)
  if (params?.from_date) searchParams.set('from_date', params.from_date)
  if (params?.to_date) searchParams.set('to_date', params.to_date)
  const qs = searchParams.toString()
  return fetchJSON<EvalSummaryData>(`${API_BASE}/api/evals/summary${qs ? `?${qs}` : ''}`)
}

export function listEvalResults(params?: {
  runtime_id?: string
  config_version?: string
  sample_name?: string
  success?: boolean
  limit?: number
  offset?: number
}): Promise<EvalResultListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.runtime_id) searchParams.set('runtime_id', params.runtime_id)
  if (params?.config_version) searchParams.set('config_version', params.config_version)
  if (params?.sample_name) searchParams.set('sample_name', params.sample_name)
  if (params?.success != null) searchParams.set('success', String(params.success))
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<EvalResultListResponse>(`${API_BASE}/api/evals/results${qs ? `?${qs}` : ''}`)
}

export function runEval(body: {
  runtime_id: string
  config_version?: string
  category?: string
}): Promise<EvalRunResponse> {
  return fetchPost<EvalRunResponse>(`${API_BASE}/api/evals/run`, body)
}

export function listConfigVersions(params?: {
  runtime_id?: string
  config_type?: string
  limit?: number
  offset?: number
}): Promise<ConfigVersionListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.runtime_id) searchParams.set('runtime_id', params.runtime_id)
  if (params?.config_type) searchParams.set('config_type', params.config_type)
  if (params?.limit != null) searchParams.set('limit', String(params.limit))
  if (params?.offset != null) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return fetchJSON<ConfigVersionListResponse>(`${API_BASE}/api/config-versions${qs ? `?${qs}` : ''}`)
}

export function createConfigVersion(body: {
  runtime_id: string
  config_type?: string
  version: string
  config_json?: Record<string, unknown>
  requires_approval?: boolean
  created_by?: string
}): Promise<ConfigVersionItem> {
  return fetchPost<ConfigVersionItem>(`${API_BASE}/api/config-versions`, body)
}

export function compareConfigs(body: {
  before_version_id: string
  after_version_id: string
}): Promise<ConfigCompareData> {
  return fetchPost<ConfigCompareData>(`${API_BASE}/api/config-versions/compare`, body)
}
