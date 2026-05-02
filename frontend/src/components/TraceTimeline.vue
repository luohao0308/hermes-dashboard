<template>
  <section class="trace-timeline">
    <div class="trace-header">
      <div>
        <h3>{{ t('trace.title') }}</h3>
        <p>{{ subtitle }}</p>
      </div>
      <span v-if="run" class="run-status" :class="run.status">{{ run.status }}</span>
    </div>

    <div v-if="spans.length > 0" class="trace-list">
      <article v-for="span in spans" :key="spanId(span)" class="trace-item" :class="span.status">
        <div class="trace-icon">{{ iconFor(span.span_type) }}</div>
        <div class="trace-body">
          <div class="trace-title">
            <strong>{{ span.title }}</strong>
            <span>{{ span.span_type }}</span>
          </div>
          <p>{{ spanSummary(span) }}</p>
          <div v-if="traceDetails(span).length" class="trace-details">
            <span v-for="detail in traceDetails(span)" :key="detail">{{ detail }}</span>
          </div>
          <div v-if="handoffPayload(span)" class="handoff-payload">
            <span>{{ t('trace.reason') }}：{{ handoffPayload(span)?.reason }}</span>
            <span>{{ t('trace.priority') }}：{{ handoffPayload(span)?.priority }}</span>
            <span>{{ t('trace.expectedOutput') }}：{{ handoffPayload(span)?.expected_output }}</span>
          </div>
          <div class="trace-meta">
            <span v-if="spanAgentName(span)">{{ spanAgentName(span) }}</span>
            <span>{{ formatTime(spanStartedAt(span)) }}</span>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-trace">
      {{ t('trace.noData') }}
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceRun, TraceSpan, WorkflowRun, WorkflowSpan } from '../types'
import { useI18n } from "vue-i18n"
import { formatTime } from '../composables/useFormatters'

const { t } = useI18n()
type GenericRun = TraceRun | WorkflowRun
type GenericSpan = TraceSpan | WorkflowSpan

const props = defineProps<{
  run: GenericRun | null
  spans: GenericSpan[]
}>()

function isWorkflowRun(run: GenericRun): run is WorkflowRun {
  return 'id' in run && !('run_id' in run)
}

function isWorkflowSpan(span: GenericSpan): span is WorkflowSpan {
  return 'id' in span && !('span_id' in span)
}

const subtitle = computed(() => {
  if (!props.run) return t('trace.noSession')
  const runId = isWorkflowRun(props.run) ? props.run.id : props.run.run_id
  return `run ${runId.slice(0, 8)} / ${props.spans.length} spans`
})

function iconFor(type: string): string {
  const map: Record<string, string> = {
    user_input: 'U',
    agent_start: 'A',
    assistant_output: 'O',
    handoff: 'H',
    tool: 'T',
    error: '!',
    llm: 'L',
    retrieval: 'R',
    guardrail: 'G',
    approval: '✓',
  }
  return map[type] || '•'
}

function spanId(span: GenericSpan): string {
  return isWorkflowSpan(span) ? span.id : span.span_id
}

function spanSummary(span: GenericSpan): string {
  if (isWorkflowSpan(span)) {
    return span.input_summary || span.output_summary || t('trace.noSummary')
  }
  return (span as TraceSpan).summary || t('trace.noSummary')
}

function spanAgentName(span: GenericSpan): string | null | undefined {
  return span.agent_name
}

function spanStartedAt(span: GenericSpan): string | null | undefined {
  return span.started_at
}

function handoffPayload(span: GenericSpan): Record<string, any> | null {
  if (span.span_type !== 'handoff') return null
  if (isWorkflowSpan(span)) return null
  return (span as TraceSpan).metadata?.handoff || null
}

function traceDetails(span: GenericSpan): string[] {
  const details: string[] = []

  if (isWorkflowSpan(span)) {
    if (span.duration_ms != null) details.push(t('trace.duration') + ' ' + span.duration_ms + 'ms')
    if (span.tool_name) details.push(t('trace.tool') + ' ' + span.tool_name)
    if (span.model_name) details.push(t('trace.model') + ' ' + span.model_name)
    if (span.input_tokens != null) details.push(t('trace.inputToken') + ' ' + span.input_tokens)
    if (span.output_tokens != null) details.push(t('trace.outputToken') + ' ' + span.output_tokens)
    if (span.cost != null) details.push(t('trace.cost') + ' $' + span.cost.toFixed(4))
    if (span.error_summary) details.push(t('trace.error') + ' ' + span.error_summary.slice(0, 80))
  } else {
    const metadata = (span as TraceSpan).metadata || {}
    const duration = durationTextLegacy(span as TraceSpan, metadata)
    if (duration) details.push(t('trace.duration') + ' ' + duration)
    if (metadata.tool_name) details.push(t('trace.tool') + ' ' + metadata.tool_name)
    if (metadata.tokens || metadata.token_count) details.push(`Token ${metadata.tokens || metadata.token_count}`)
    if (metadata.input_summary) details.push(t("trace.inputToken") + " " + String(metadata.input_summary).slice(0, 80))
    if (metadata.output_summary) details.push(t("trace.outputToken") + " " + String(metadata.output_summary).slice(0, 80))
  }

  return details
}

function durationTextLegacy(span: TraceSpan, metadata: Record<string, any>): string {
  if (typeof metadata.duration_ms === 'number') return `${metadata.duration_ms}ms`
  const start = new Date(span.started_at)
  const end = new Date(span.completed_at || '')
  if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && end >= start) {
    const ms = end.getTime() - start.getTime()
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
  }
  return ''
}
</script>

<style scoped>
.trace-timeline {
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.trace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.trace-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 800;
}

.trace-header p {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.run-status {
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: var(--success-soft);
  color: var(--success-color);
  font-size: 11px;
  font-weight: 800;
}

.run-status.error {
  background: var(--error-soft);
  color: var(--error-color);
}

.run-status.running {
  background: var(--warning-soft);
  color: var(--warning-color);
}

.trace-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trace-item {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
}

.trace-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent-color);
  font-size: 12px;
  font-weight: 900;
}

.trace-item.error .trace-icon {
  background: var(--error-soft);
  color: var(--error-color);
}

.trace-body {
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.trace-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trace-title strong {
  color: var(--text-primary);
  font-size: 13px;
}

.trace-title span,
.trace-meta {
  color: var(--text-muted);
  font-size: 11px;
}

.trace-body p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.trace-details,
.handoff-payload {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.trace-details span,
.handoff-payload span {
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.trace-meta {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.empty-trace {
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  background: var(--bg-primary);
}
</style>
