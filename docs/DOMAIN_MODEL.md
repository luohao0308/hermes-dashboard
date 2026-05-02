# Domain Model

## Overview

The AI Workflow Control Plane is built around eight core domain objects. These objects are runtime-agnostic -- they do not depend on any specific Agent framework, LLM provider, or automation system.

## Entity Relationship

```
Runtime 1──N Run 1──N Task
                │
                ├── N TraceSpan
                │       │
                │       └── N ToolCall ──0..1 Approval
                │
                ├── N Artifact
                │
                └── 0..1 RCAReport ──0..1 Runbook

Runtime 1──N EvalResult
Runtime 1──N ConnectorConfig
```

## Core Objects

### Runtime

An external AI runtime or automation system that emits workflow events into the control plane.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | string | Display name |
| type | enum | `agent_sdk`, `ci_cd`, `code_review`, `custom` |
| status | enum | `active`, `inactive`, `error` |
| config_json | JSON | Runtime-specific configuration |
| created_at | timestamp | Registration time |
| updated_at | timestamp | Last update time |

### Run

A complete AI workflow execution. One runtime can have many runs.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| runtime_id | UUID | FK to Runtime |
| title | string | Human-readable run title |
| status | enum | `queued`, `running`, `waiting_approval`, `completed`, `failed`, `cancelled` |
| input_summary | text | Brief description of the run input |
| output_summary | text | Brief description of the run output |
| error_summary | text | Error description if failed |
| started_at | timestamp | Execution start time |
| ended_at | timestamp | Execution end time |
| duration_ms | integer | Total duration in milliseconds |
| total_tokens | integer | Sum of input + output tokens |
| total_cost | decimal | Total cost in USD |
| metadata_json | JSON | Arbitrary metadata |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last update time |

### Task

A schedulable unit inside a Run. Tasks can have dependencies forming a DAG.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK to Run |
| parent_task_id | UUID | FK to Task (nullable, for subtasks) |
| title | string | Task title |
| status | enum | `pending`, `ready`, `running`, `blocked`, `completed`, `failed`, `skipped` |
| task_type | string | Task type identifier |
| depends_on_json | JSON | Array of task IDs this task depends on |
| started_at | timestamp | Start time |
| ended_at | timestamp | End time |
| duration_ms | integer | Duration in milliseconds |
| error_summary | text | Error description if failed |
| metadata_json | JSON | Arbitrary metadata |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last update time |

### TraceSpan

An observable event or operation inside a Run. Spans form a tree via parent_span_id.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK to Run |
| task_id | UUID | FK to Task (nullable) |
| parent_span_id | UUID | FK to TraceSpan (nullable, for nesting) |
| span_type | enum | `model_call`, `tool_call`, `handoff`, `approval`, `system_event`, `error`, `artifact`, `eval` |
| title | string | Span title |
| status | enum | `running`, `completed`, `failed`, `cancelled` |
| agent_name | string | Agent or component name (nullable) |
| model_name | string | LLM model name (nullable) |
| tool_name | string | Tool name (nullable) |
| input_summary | text | Brief input description |
| output_summary | text | Brief output description |
| error_summary | text | Error description if failed |
| started_at | timestamp | Start time |
| ended_at | timestamp | End time |
| duration_ms | integer | Duration in milliseconds |
| input_tokens | integer | Input token count |
| output_tokens | integer | Output token count |
| cost | decimal | Cost in USD |
| metadata_json | JSON | Arbitrary metadata |
| created_at | timestamp | Creation time |

### ToolCall

A governed tool invocation. Linked to a TraceSpan of type `tool_call`.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK to Run |
| span_id | UUID | FK to TraceSpan |
| tool_name | string | Tool identifier |
| risk_level | enum | `read`, `write`, `execute`, `network`, `destructive` |
| decision | enum | `allow`, `confirm`, `deny` |
| status | enum | `pending`, `approved`, `denied`, `executed`, `failed` |
| input_json | JSON | Tool input parameters |
| output_json | JSON | Tool output result |
| error_summary | text | Error description if failed |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last update time |

### Approval

A human approval event for gated workflow actions.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK to Run |
| tool_call_id | UUID | FK to ToolCall (nullable) |
| status | enum | `pending`, `approved`, `rejected`, `expired` |
| reason | text | Why approval was requested |
| requested_by | string | System or component that requested |
| resolved_by | string | Human who resolved |
| resolved_note | text | Resolution note |
| expires_at | timestamp | Expiration time |
| created_at | timestamp | Creation time |
| resolved_at | timestamp | Resolution time |

### Artifact

A workflow output or evidence item.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK to Run |
| task_id | UUID | FK to Task (nullable) |
| span_id | UUID | FK to TraceSpan (nullable) |
| artifact_type | enum | `markdown`, `json`, `code_diff`, `log_excerpt`, `report`, `runbook`, `rca` |
| title | string | Artifact title |
| content_text | text | Inline text content (nullable) |
| content_json | JSON | Inline JSON content (nullable) |
| storage_url | string | External storage URL (nullable) |
| created_at | timestamp | Creation time |

### EvalResult

An evaluation record for a runtime, model, prompt, or configuration.

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| runtime_id | UUID | FK to Runtime |
| run_id | UUID | FK to Run (nullable) |
| config_version | string | Configuration version identifier |
| sample_name | string | Eval sample name |
| success | boolean | Whether the eval passed |
| score | decimal | Numeric score |
| latency_ms | integer | Execution latency |
| cost | decimal | Cost in USD |
| metrics_json | JSON | Additional metrics |
| created_at | timestamp | Creation time |

## Design Principles

1. **Runtime-agnostic**: No field assumes a specific Agent framework or LLM provider.
2. **Trace-first**: Every observable behavior is a TraceSpan. Tool calls, model calls, approvals, and errors are all spans.
3. **Evidence-based**: RCA and Runbook reference specific spans, tool calls, and artifacts as evidence.
4. **Governable**: Tool calls carry risk levels and decisions. High-risk actions require approval.
5. **Extensible**: JSON metadata fields allow runtime-specific data without schema changes.
