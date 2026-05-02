// API client for run-based RCA and Runbook — v1.2

import type { RcaReport, RunbookReport } from '../types'
import { fetchJSON, fetchPost } from './useApi'

const BASE = '/api/runs'

export function generateRca(runId: string): Promise<RcaReport> {
  return fetchPost<RcaReport>(`${BASE}/${runId}/rca`, {})
}

export function getLatestRca(runId: string): Promise<RcaReport> {
  return fetchJSON<RcaReport>(`${BASE}/${runId}/rca`)
}

export function generateRunbook(runId: string): Promise<RunbookReport> {
  return fetchPost<RunbookReport>(`${BASE}/${runId}/runbook`, {})
}

export function getLatestRunbook(runId: string): Promise<RunbookReport> {
  return fetchJSON<RunbookReport>(`${BASE}/${runId}/runbook`)
}

export function exportArtifact(
  runId: string,
  kind: 'rca' | 'runbook',
): Promise<{ artifact_id: string; title: string; content_text: string }> {
  return fetchPost(`${BASE}/${runId}/export`, { kind })
}
