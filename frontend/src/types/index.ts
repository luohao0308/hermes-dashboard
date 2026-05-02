// Shared type definitions for Hermes frontend

export interface Task {
  task_id: string
  name: string
  status: 'running' | 'pending' | 'completed'
  progress: number
  message_count?: number
  model?: string
  started_at?: string
  elapsed?: number
  estimated_end?: string
}

export interface Log {
  id?: number
  timestamp: string
  message: string
  type: 'info' | 'warning' | 'error' | 'debug'
  source?: string
}

export type LogItem = Log

export interface HistoryItem {
  task_id: string
  name: string
  completed_at: string
  duration: number
  status: 'success' | 'failed' | 'cancelled'
  message_count?: number
  model?: string
  input_tokens?: number
  output_tokens?: number
}

export interface SessionMessage {
  role?: string
  content?: string
  text?: string
  message?: string
  timestamp?: string
  created_at?: string
}

export interface SessionDetailData {
  task_id?: string
  name?: string
  status?: string
  messages?: SessionMessage[]
  message_count?: number
  model?: string
  started_at?: string
  completed_at?: string
  duration?: number
  input_tokens?: number
  output_tokens?: number
  end_reason?: string
  logs?: Log[]
  history?: HistoryItem[]
  traces?: TraceRun[]
}

export interface TraceRun {
  run_id: string
  session_id: string
  agent_id: string
  linked_session_id?: string | null
  input_summary?: string
  status: string
  started_at: string
  completed_at?: string | null
  metadata?: Record<string, unknown>
}

export interface TraceSpan {
  span_id: string
  run_id: string
  span_type: string
  title: string
  summary?: string
  agent_name?: string | null
  status: string
  started_at: string
  completed_at?: string | null
  metadata?: Record<string, unknown>
}

export interface RcaEvidence {
  source: string
  title: string
  detail: string
  severity: 'high' | 'medium' | 'low'
  timestamp?: string | null
  ref?: string | null
}

export interface RcaReport {
  report_id: string
  session_id: string
  run_id?: string | null
  category: string
  root_cause: string
  confidence: number
  evidence: RcaEvidence[]
  next_actions: string[]
  low_confidence: boolean
  generated_at: string
  analyzer: string
}

export interface RunbookStep {
  step_id: string
  label: string
  action_type: string
  requires_confirmation: boolean
  status: string
}

export interface RunbookReport {
  runbook_id: string
  session_id: string
  run_id?: string | null
  rca_report_id?: string | null
  title: string
  severity: string
  summary: string
  checklist: string[]
  execution_steps?: RunbookStep[]
  evidence_count: number
  markdown: string
  generated_at: string
  generator: string
}

export interface OverviewSnapshot {
  health?: Record<string, unknown> | null
  analytics?: Record<string, unknown> | null
  evalSummary?: Record<string, unknown> | null
  modelInfo?: Record<string, unknown> | null
  config?: Record<string, unknown> | null
  skills?: Record<string, unknown> | unknown[] | null
  cronJobs?: Record<string, unknown> | unknown[] | null
  plugins?: Record<string, unknown> | unknown[] | null
}

export interface AlertItem {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  source: string
  session_id?: string | null
  action_label: string
  action_nav: string
  created_at: string
}

export interface EvalSummary {
  total?: number
  passed?: number
  failed?: number
  score?: number
  details?: Record<string, unknown>
}

export interface ToastMessage {
  id: number
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
}

// ---------------------------------------------------------------------------
// Generic Workflow Observability types (v1.0 API)
// ---------------------------------------------------------------------------

export interface WorkflowRuntime {
  id: string
  name: string
  type: string
  status: string
  config_json?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorkflowRun {
  id: string
  runtime_id: string
  title: string
  status: string
  input_summary?: string | null
  output_summary?: string | null
  error_summary?: string | null
  started_at?: string | null
  ended_at?: string | null
  duration_ms?: number | null
  total_tokens?: number | null
  total_cost?: number | null
  metadata_json?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorkflowSpan {
  id: string
  run_id: string
  task_id?: string | null
  parent_span_id?: string | null
  span_type: string
  title: string
  status: string
  agent_name?: string | null
  model_name?: string | null
  tool_name?: string | null
  input_summary?: string | null
  output_summary?: string | null
  error_summary?: string | null
  started_at?: string | null
  ended_at?: string | null
  duration_ms?: number | null
  input_tokens?: number | null
  output_tokens?: number | null
  cost?: number | null
  metadata_json?: Record<string, unknown> | null
  created_at: string
}

export interface WorkflowRunListResponse {
  items: WorkflowRun[]
  total: number
  limit: number
  offset: number
  next_cursor?: string | null
  has_more: boolean
}

export interface WorkflowTraceResponse {
  run: WorkflowRun
  spans: WorkflowSpan[]
}

// ---------------------------------------------------------------------------
// Tool Governance types (v1.1 API)
// ---------------------------------------------------------------------------

export interface ApprovalItem {
  id: string
  run_id: string
  tool_call_id?: string | null
  status: string
  reason?: string | null
  requested_by?: string | null
  resolved_by?: string | null
  resolved_note?: string | null
  expires_at?: string | null
  created_at: string
  resolved_at?: string | null
}

export interface ApprovalListResponse {
  items: ApprovalItem[]
  total: number
  limit: number
  offset: number
  next_cursor?: string | null
  has_more: boolean
}

export interface ToolPolicyItem {
  risk_level: string
  decision: string
  description: string
}

export interface ToolPolicyListResponse {
  policies: ToolPolicyItem[]
}

// ---------------------------------------------------------------------------
// Connector Framework types (v1.3 API)
// ---------------------------------------------------------------------------

export interface ConnectorConfig {
  id: string
  runtime_id: string
  connector_type: string
  display_name: string
  enabled: boolean
  config_json?: Record<string, unknown> | null
  secret_ref?: string | null
  created_at: string
  updated_at: string
}

export interface ConnectorListResponse {
  items: ConnectorConfig[]
  total: number
}

// ---------------------------------------------------------------------------
// Eval & Config Version types (v1.4 API)
// ---------------------------------------------------------------------------

export interface EvalResultItem {
  id: string
  runtime_id: string
  run_id?: string | null
  config_version?: string | null
  sample_name?: string | null
  success?: boolean | null
  score?: number | null
  latency_ms?: number | null
  cost?: number | null
  metrics_json?: Record<string, unknown> | null
  created_at: string
}

export interface EvalTrendPoint {
  date: string
  runs: number
  passed: number
  failed: number
  avg_score?: number | null
  avg_latency_ms?: number | null
  avg_cost?: number | null
  tool_error_rate?: number | null
  handoff_count?: number | null
  approval_count?: number | null
}

export interface EvalRuntimeBreakdown {
  runtime_id: string
  runtime_name: string
  total: number
  passed: number
  failed: number
  avg_score?: number | null
}

export interface EvalConfigBreakdown {
  config_version: string
  total: number
  passed: number
  failed: number
  avg_score?: number | null
}

export interface EvalSummaryData {
  total: number
  passed: number
  failed: number
  avg_score?: number | null
  avg_latency_ms?: number | null
  avg_cost?: number | null
  tool_error_rate?: number | null
  handoff_count?: number | null
  approval_count?: number | null
  by_runtime: EvalRuntimeBreakdown[]
  by_config_version: EvalConfigBreakdown[]
  trend: EvalTrendPoint[]
}

export interface EvalResultListResponse {
  items: EvalResultItem[]
  total: number
  limit: number
  offset: number
}

export interface ConfigVersionItem {
  id: string
  runtime_id: string
  config_type: string
  version: string
  config_json?: Record<string, unknown> | null
  evaluation_score?: number | null
  requires_approval: boolean
  created_by?: string | null
  created_at: string
}

export interface ConfigVersionListResponse {
  items: ConfigVersionItem[]
  total: number
}

export interface ConfigFieldChange {
  field: string
  before: unknown
  after: unknown
}

export interface ConfigCompareData {
  before: ConfigVersionItem
  after: ConfigVersionItem
  score_delta?: number | null
  changes: ConfigFieldChange[]
  requires_approval: boolean
  recommended?: boolean
}

// ---------------------------------------------------------------------------
// Workflow Orchestration types (v2.0 API)
// ---------------------------------------------------------------------------

export interface RetryPolicy {
  max_retries: number
  backoff_seconds: number
}

export interface WorkflowNodeDef {
  id: string
  workflow_id: string
  node_id: string
  title: string
  task_type: string
  config?: Record<string, unknown> | null
  retry_policy?: RetryPolicy | null
  timeout_seconds?: number | null
  approval_timeout_seconds?: number | null
  created_at: string
}

export interface WorkflowEdgeDef {
  id: string
  workflow_id: string
  from_node: string
  to_node: string
}

export interface WorkflowDefinition {
  id: string
  runtime_id: string
  name: string
  description?: string | null
  version: number
  timeout_seconds?: number | null
  max_concurrent_tasks?: number | null
  created_at: string
  updated_at: string
  nodes: WorkflowNodeDef[]
  edges: WorkflowEdgeDef[]
}

export interface WorkflowDefinitionListResponse {
  items: WorkflowDefinition[]
  total: number
}

export interface WorkflowTaskItem {
  id: string
  run_id: string
  node_id?: string | null
  title: string
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled' | 'dead_letter'
  task_type?: string | null
  depends_on_json?: Record<string, unknown> | null
  started_at?: string | null
  ended_at?: string | null
  duration_ms?: number | null
  error_summary?: string | null
  retry_count: number
  locked_by?: string | null
  locked_at?: string | null
  next_retry_at?: string | null
  metadata_json?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorkflowRunDetail {
  id: string
  runtime_id: string
  workflow_id?: string | null
  title: string
  status: string
  input_summary?: string | null
  output_summary?: string | null
  error_summary?: string | null
  started_at?: string | null
  ended_at?: string | null
  duration_ms?: number | null
  total_tokens?: number | null
  total_cost?: number | null
  metadata_json?: Record<string, unknown> | null
  created_at: string
  updated_at: string
  tasks: WorkflowTaskItem[]
}

export interface WorkflowRunDetailListResponse {
  items: WorkflowRunDetail[]
  total: number
}

// ---------------------------------------------------------------------------
// Workflow Version History types (OPT-52)
// ---------------------------------------------------------------------------

export interface WorkflowVersionHistoryItem {
  id: string
  workflow_id: string
  version: number
  name: string
  description?: string | null
  nodes_json?: Record<string, unknown>[] | null
  edges_json?: Record<string, unknown>[] | null
  timeout_seconds?: number | null
  max_concurrent_tasks?: number | null
  created_at: string
  created_by?: string | null
}

export interface WorkflowVersionListResponse {
  items: WorkflowVersionHistoryItem[]
  total: number
}

// ---------------------------------------------------------------------------
// Failed Event types (OPT-54)
// ---------------------------------------------------------------------------

export interface FailedEventItem {
  id: string
  connector_id: string
  event_type: string
  event_id?: string | null
  run_id?: string | null
  payload?: Record<string, unknown> | null
  error_message: string
  created_at: string
}

export interface FailedEventListResponse {
  items: FailedEventItem[]
  total: number
}

// ---------------------------------------------------------------------------
// Batch Approval types (OPT-55)
// ---------------------------------------------------------------------------

export interface BatchApprovalResult {
  id: string
  status: string
}

export interface BatchApprovalResponse {
  processed: number
  skipped: number
  results: BatchApprovalResult[]
}
