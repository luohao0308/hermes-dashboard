<template>
  <section class="trace-timeline">
    <div class="trace-header">
      <div>
        <h3>Trace 时间线</h3>
        <p>{{ subtitle }}</p>
      </div>
      <span v-if="run" class="run-status" :class="run.status">{{ run.status }}</span>
    </div>

    <div v-if="spans.length > 0" class="trace-list">
      <article v-for="span in spans" :key="span.span_id" class="trace-item" :class="span.status">
        <div class="trace-icon">{{ iconFor(span.span_type) }}</div>
        <div class="trace-body">
          <div class="trace-title">
            <strong>{{ span.title }}</strong>
            <span>{{ span.span_type }}</span>
          </div>
          <p>{{ span.summary || '无摘要' }}</p>
          <div v-if="handoffPayload(span)" class="handoff-payload">
            <span>原因：{{ handoffPayload(span)?.reason }}</span>
            <span>优先级：{{ handoffPayload(span)?.priority }}</span>
            <span>期望产物：{{ handoffPayload(span)?.expected_output }}</span>
          </div>
          <div class="trace-meta">
            <span v-if="span.agent_name">{{ span.agent_name }}</span>
            <span>{{ formatTime(span.started_at) }}</span>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-trace">
      暂无 trace 数据
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TraceRun {
  run_id: string
  session_id: string
  agent_id: string
  linked_session_id?: string | null
  input_summary?: string
  status: string
  started_at: string
  completed_at?: string | null
  metadata?: Record<string, any>
}

interface TraceSpan {
  span_id: string
  run_id: string
  span_type: string
  title: string
  summary?: string
  agent_name?: string | null
  status: string
  started_at: string
  completed_at?: string | null
  metadata?: Record<string, any>
}

const props = defineProps<{
  run: TraceRun | null
  spans: TraceSpan[]
}>()

const subtitle = computed(() => {
  if (!props.run) return '当前 session 还没有关联 Agent run'
  return `run ${props.run.run_id.slice(0, 8)} / ${props.spans.length} spans`
})

function iconFor(type: string): string {
  const map: Record<string, string> = {
    user_input: 'U',
    agent_start: 'A',
    assistant_output: 'O',
    handoff: 'H',
    tool: 'T',
    error: '!',
  }
  return map[type] || '•'
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function handoffPayload(span: TraceSpan): Record<string, any> | null {
  if (span.span_type !== 'handoff') return null
  return span.metadata?.handoff || null
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

.handoff-payload {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

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
