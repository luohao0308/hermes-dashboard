<template>
  <div class="workflow-detail">
    <div class="section-header">
      <button class="btn btn-ghost" @click="$emit('back')">
        <ArrowLeft :size="15" />
        {{ t('common.back') }}
      </button>
      <div class="workflow-heading">
        <div class="workflow-icon">
          <GitBranch :size="22" />
        </div>
        <div>
          <h2 class="section-title">{{ workflow.name }}</h2>
          <p v-if="workflow.description" class="wf-desc">{{ workflow.description }}</p>
        </div>
      </div>
      <span class="card-badge">v{{ workflow.version }}</span>
      <button class="btn btn-primary" @click="$emit('startRun')">
        <Play :size="15" />
        {{ t('workflows.startRun') }}
      </button>
    </div>

    <div class="workflow-grid">
      <div class="dag-section">
        <div class="canvas-header">
          <div class="canvas-tabs">
            <button class="active">Visual Editor</button>
            <button>JSON Config</button>
          </div>
          <div class="canvas-actions">
            <button><Plus :size="14" /></button>
            <button><Search :size="14" /></button>
          </div>
        </div>
        <div class="dag-container">
          <svg class="dag-svg" :viewBox="svgViewBox">
            <line
              v-for="(edge, i) in layoutEdges"
              :key="'e-' + i"
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              class="dag-edge"
            />
            <polygon
              v-for="(edge, i) in layoutEdges"
              :key="'a-' + i"
              :points="arrowPoints(edge)"
              class="dag-arrow"
            />
            <g v-for="node in layoutNodes" :key="node.node_id" :transform="`translate(${node.x}, ${node.y})`">
              <rect :width="NODE_W" :height="NODE_H" rx="12" class="dag-node" :class="nodeStatusClass(node.node_id)" />
              <text :x="NODE_W / 2" :y="NODE_H / 2 - 6" text-anchor="middle" class="dag-node-label">
                {{ node.title }}
              </text>
              <text :x="NODE_W / 2" :y="NODE_H / 2 + 12" text-anchor="middle" class="dag-node-type">
                {{ node.task_type }}
              </text>
            </g>
          </svg>
        </div>
      </div>

      <aside class="workflow-side">
        <div class="side-card">
          <div class="side-card-header">
            <History :size="16" />
            <h3>{{ t('workflows.versions') }}</h3>
            <button @click="$emit('loadVersions')" :disabled="loadingVersions">
              {{ loadingVersions ? t('common.loading') : t('common.refresh') }}
            </button>
          </div>
          <div v-if="!versions || versions.length === 0" class="empty-hint">{{ t('workflows.noVersions') }}</div>
          <div v-else class="version-list">
            <div v-for="v in versions" :key="v.id" class="version-item">
              <div>
                <strong>v{{ v.version }}</strong>
                <small>{{ formatTime(v.created_at) }} / {{ v.created_by || '-' }}</small>
              </div>
              <button class="rollback-btn" @click="$emit('rollback', v.version)" :disabled="rollingBack">
                {{ t('workflows.rollback') }}
              </button>
            </div>
          </div>
        </div>

        <div class="side-card">
          <div class="side-card-header">
            <Settings :size="16" />
            <h3>Workflow Settings</h3>
          </div>
          <div class="setting-row">
            <span>Retry Strategy</span>
            <strong>Per node</strong>
          </div>
          <div class="setting-row">
            <span>Timeout Policy</span>
            <strong>{{ workflow.nodes.length }} nodes</strong>
          </div>
          <div class="setting-row">
            <span>DAG Edges</span>
            <strong>{{ workflow.edges.length }}</strong>
          </div>
        </div>
      </aside>
    </div>

    <div class="nodes-section">
      <h3 class="sub-title">{{ t('workflows.nodes') }} ({{ workflow.nodes.length }})</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('workflows.nodes') }} ID</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>Retries</th>
            <th>Timeout</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="node in workflow.nodes" :key="node.id">
            <td class="mono">{{ node.node_id }}</td>
            <td>{{ node.title }}</td>
            <td>{{ node.task_type }}</td>
            <td>{{ node.retry_policy?.max_retries ?? 3 }}</td>
            <td>{{ node.timeout_seconds ? node.timeout_seconds + 's' : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="runs-section">
      <div class="runs-header">
        <h3 class="sub-title">{{ t('runs.title') }}</h3>
        <button class="btn btn-primary" @click="$emit('startRun')">{{ t('workflows.startRun') }}</button>
      </div>
      <div v-if="runs.length === 0" class="empty-hint">{{ t('runs.noRuns') }}</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>{{ t('runs.runId') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('workflows.nodes') }}</th>
            <th>{{ t('runs.startTime') }}</th>
            <th>{{ t('runs.duration') }}</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.id"
            class="clickable"
            :class="{ selected: activeRun?.id === run.id }"
            @click="$emit('selectRun', run)"
          >
            <td class="mono">{{ run.id.slice(0, 8) }}</td>
            <td>
              <span :class="['status-chip', statusClass(run.status)]">{{ run.status }}</span>
            </td>
            <td>{{ run.tasks.length }}</td>
            <td>{{ run.started_at ? formatTime(run.started_at) : '-' }}</td>
            <td>{{ run.duration_ms ? formatDuration(run.duration_ms) : '-' }}</td>
            <td>
              <div class="run-actions" @click.stop>
                <button v-if="run.status === 'running'" @click="$emit('pauseRun', run)">Pause</button>
                <button v-if="run.status === 'paused'" @click="$emit('resumeRun', run)">Resume</button>
                <button v-if="canRetry(run.status)" @click="$emit('retryRun', run)">Retry</button>
                <button v-if="canCancel(run.status)" class="danger" @click="$emit('cancelRun', run)">Cancel</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="activeRun" class="run-observability">
      <div class="runs-header">
        <div>
          <h3 class="sub-title">Run Tasks</h3>
          <p class="run-subtitle">{{ activeRun.title }} / {{ activeRun.id.slice(0, 8) }}</p>
        </div>
        <span :class="['status-chip', statusClass(activeRun.status)]">{{ activeRun.status }}</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Node</th>
            <th>Status</th>
            <th>Retries</th>
            <th>Worker</th>
            <th>Next Retry</th>
            <th>{{ t('runs.duration') }}</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in activeRun.tasks" :key="task.id">
            <td>
              <span class="mono">{{ task.node_id || task.id.slice(0, 8) }}</span>
              <small>{{ task.title }}</small>
            </td>
            <td><span :class="['status-chip', statusClass(task.status)]">{{ task.status }}</span></td>
            <td>{{ task.retry_count }}</td>
            <td>
              <span v-if="task.locked_by" class="mono">{{ task.locked_by }}</span>
              <span v-else>-</span>
              <small v-if="task.locked_at">{{ formatTime(task.locked_at) }}</small>
            </td>
            <td>{{ task.next_retry_at ? formatTime(task.next_retry_at) : '-' }}</td>
            <td>{{ task.duration_ms ? formatDuration(task.duration_ms) : '-' }}</td>
            <td class="error-cell">{{ task.error_summary || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, GitBranch, History, Play, Plus, Search, Settings } from 'lucide-vue-next'
import type { WorkflowDefinition, WorkflowRunDetail, WorkflowVersionHistoryItem } from '../types'

const { t } = useI18n()

const props = defineProps<{
  workflow: WorkflowDefinition
  runs: WorkflowRunDetail[]
  selectedRun?: WorkflowRunDetail | null
  taskStatuses?: Record<string, string>
  versions?: WorkflowVersionHistoryItem[]
  loadingVersions?: boolean
  rollingBack?: boolean
}>()

defineEmits<{
  back: []
  startRun: []
  selectRun: [run: WorkflowRunDetail]
  pauseRun: [run: WorkflowRunDetail]
  resumeRun: [run: WorkflowRunDetail]
  retryRun: [run: WorkflowRunDetail]
  cancelRun: [run: WorkflowRunDetail]
  loadVersions: []
  rollback: [version: number]
}>()

const NODE_W = 176
const NODE_H = 64
const GAP_X = 72
const GAP_Y = 44

interface LayoutNode {
  node_id: string
  title: string
  task_type: string
  x: number
  y: number
}

interface LayoutEdge {
  x1: number
  y1: number
  x2: number
  y2: number
}

const layoutNodes = computed<LayoutNode[]>(() => {
  const nodes = props.workflow.nodes
  const edges = props.workflow.edges
  if (nodes.length === 0) return []

  const inDegree: Record<string, number> = {}
  const adj: Record<string, string[]> = {}
  for (const n of nodes) {
    inDegree[n.node_id] = 0
    adj[n.node_id] = []
  }
  for (const e of edges) {
    adj[e.from_node] = [...(adj[e.from_node] ?? []), e.to_node]
    inDegree[e.to_node] = (inDegree[e.to_node] ?? 0) + 1
  }

  const level: Record<string, number> = {}
  const queue: string[] = []
  for (const n of nodes) {
    if ((inDegree[n.node_id] ?? 0) === 0) {
      queue.push(n.node_id)
      level[n.node_id] = 0
    }
  }
  while (queue.length > 0) {
    const cur = queue.shift()!
    for (const next of adj[cur] ?? []) {
      level[next] = Math.max(level[next] ?? 0, (level[cur] ?? 0) + 1)
      inDegree[next]!--
      if (inDegree[next] === 0) queue.push(next)
    }
  }

  const byLevel: Record<number, string[]> = {}
  for (const n of nodes) {
    const lv = level[n.node_id] ?? 0
    if (!byLevel[lv]) byLevel[lv] = []
    byLevel[lv].push(n.node_id)
  }

  const nodeMap: Record<string, (typeof nodes)[0]> = {}
  for (const n of nodes) nodeMap[n.node_id] = n

  const result: LayoutNode[] = []
  const sortedLevels = Object.keys(byLevel).map(Number).sort((a, b) => a - b)
  for (const lv of sortedLevels) {
    const ids = byLevel[lv]
    ids.forEach((id, col) => {
      const n = nodeMap[id]
      result.push({
        node_id: n.node_id,
        title: n.title,
        task_type: n.task_type,
        x: 32 + lv * (NODE_W + GAP_X),
        y: 32 + col * (NODE_H + GAP_Y),
      })
    })
  }
  return result
})

const layoutEdges = computed<LayoutEdge[]>(() => {
  const posMap: Record<string, LayoutNode> = {}
  for (const n of layoutNodes.value) posMap[n.node_id] = n
  return props.workflow.edges
    .filter((e) => posMap[e.from_node] && posMap[e.to_node])
    .map((e) => {
      const from = posMap[e.from_node]
      const to = posMap[e.to_node]
      return {
        x1: from.x + NODE_W,
        y1: from.y + NODE_H / 2,
        x2: to.x,
        y2: to.y + NODE_H / 2,
      }
    })
})

const activeRun = computed(() => props.selectedRun ?? props.runs[0] ?? null)

const svgViewBox = computed(() => {
  if (layoutNodes.value.length === 0) return '0 0 520 260'
  const maxX = Math.max(...layoutNodes.value.map((n) => n.x + NODE_W)) + 36
  const maxY = Math.max(...layoutNodes.value.map((n) => n.y + NODE_H)) + 36
  return `0 0 ${maxX} ${maxY}`
})

function arrowPoints(edge: LayoutEdge): string {
  const size = 8
  const dx = edge.x2 - edge.x1
  const dy = edge.y2 - edge.y1
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len === 0) return ''
  const ux = dx / len
  const uy = dy / len
  const px = -uy
  const py = ux
  const tipX = edge.x2
  const tipY = edge.y2
  return `${tipX},${tipY} ${tipX - size * ux + size * 0.4 * px},${tipY - size * uy + size * 0.4 * py} ${tipX - size * ux - size * 0.4 * px},${tipY - size * uy - size * 0.4 * py}`
}

function nodeStatusClass(nodeId: string): string {
  const status = props.taskStatuses?.[nodeId] ?? activeRun.value?.tasks.find((task) => task.node_id === nodeId)?.status
  if (!status) return ''
  return `status-${status}`
}

function statusClass(status: string): string {
  if (status === 'completed') return 'status-success'
  if (status === 'failed') return 'status-error'
  if (status === 'running') return 'status-running'
  if (status === 'paused') return 'status-paused'
  if (status === 'dead_letter') return 'status-dead-letter'
  if (status === 'cancelled') return 'status-cancelled'
  if (status === 'waiting_approval') return 'status-waiting'
  return 'status-pending'
}

function canCancel(status: string): boolean {
  return !['completed', 'failed', 'cancelled'].includes(status)
}

function canRetry(status: string): boolean {
  return ['failed', 'cancelled'].includes(status)
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}
</script>

<style scoped>
.workflow-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section-header,
.dag-section,
.side-card,
.nodes-section,
.runs-section,
.run-observability {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
}

.workflow-heading {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.workflow-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #dbeafe;
  color: #1d4ed8;
}

.section-title {
  margin: 0;
  color: #0f172a;
  font-size: 20px;
  font-weight: 900;
}

.wf-desc {
  margin: 2px 0 0;
  color: #64748b;
  font-size: 12px;
}

.workflow-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
}

.dag-section {
  overflow: hidden;
}

.canvas-header,
.runs-header,
.side-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: #f8fafc;
}

.canvas-header {
  padding: 14px 16px;
}

.canvas-tabs {
  display: flex;
  gap: 14px;
}

.canvas-tabs button,
.canvas-actions button,
.side-card-header button,
.rollback-btn,
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.canvas-tabs button {
  border: 0;
  background: transparent;
  color: #94a3b8;
}

.canvas-tabs button.active {
  color: #2563eb;
}

.canvas-actions {
  display: flex;
  gap: 8px;
}

.canvas-actions button {
  width: 30px;
  height: 30px;
}

.btn {
  min-height: 34px;
  gap: 7px;
  padding: 0 12px;
}

.btn-primary {
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
}

.btn-ghost {
  background: #ffffff;
}

.card-badge {
  padding: 5px 9px;
  border-radius: 999px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 11px;
  font-weight: 900;
}

.dag-container {
  min-height: 440px;
  overflow: auto;
  background:
    radial-gradient(#e2e8f0 1px, transparent 1px),
    #ffffff;
  background-size: 24px 24px;
}

.dag-svg {
  min-width: 640px;
  min-height: 440px;
}

.dag-edge {
  stroke: #cbd5e1;
  stroke-width: 2;
}

.dag-arrow {
  fill: #cbd5e1;
}

.dag-node {
  fill: #ffffff;
  stroke: #cbd5e1;
  stroke-width: 2;
  filter: drop-shadow(0 6px 12px rgba(15, 23, 42, 0.08));
}

.dag-node.status-completed { fill: #ecfdf5; stroke: #10b981; }
.dag-node.status-running { fill: #eff6ff; stroke: #2563eb; }
.dag-node.status-failed { fill: #fff1f2; stroke: #ef4444; }
.dag-node.status-dead_letter { fill: #f5f3ff; stroke: #7c3aed; }
.dag-node.status-cancelled { fill: #f8fafc; stroke: #64748b; }
.dag-node.status-waiting_approval { fill: #fffbeb; stroke: #f59e0b; }

.dag-node-label {
  fill: #0f172a;
  font-size: 13px;
  font-weight: 800;
}

.dag-node-type {
  fill: #94a3b8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workflow-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.side-card {
  overflow: hidden;
}

.side-card-header {
  min-height: 52px;
  padding: 0 16px;
}

.side-card-header h3,
.sub-title {
  margin: 0;
  color: #0f172a;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.side-card-header h3 {
  flex: 1;
}

.side-card-header button,
.rollback-btn {
  min-height: 28px;
  padding: 0 10px;
}

.version-list {
  display: flex;
  flex-direction: column;
}

.version-item,
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 16px;
  border-top: 1px solid var(--border-subtle);
}

.version-item strong,
.setting-row strong {
  color: #0f172a;
  font-size: 13px;
}

.version-item small,
.setting-row span {
  display: block;
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
}

.nodes-section,
.runs-section,
.run-observability {
  padding: 18px;
}

.nodes-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.runs-header {
  margin: -18px -18px 14px;
  padding: 14px 18px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 12px;
}

.data-table th {
  padding: 12px 14px;
  color: #94a3b8;
  background: #f8fafc;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
}

.data-table td {
  padding: 12px 14px;
  border-top: 1px solid var(--border-subtle);
  color: #475569;
  font-size: 12px;
}

.data-table .clickable {
  cursor: pointer;
}

.data-table .clickable:hover td {
  background: #f8fafc;
}

.data-table .clickable.selected td {
  background: #eff6ff;
}

.data-table small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.run-subtitle {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
}

.error-cell {
  max-width: 260px;
  overflow-wrap: anywhere;
}

.mono {
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 800;
}

.status-chip {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.status-success { color: #047857; background: #ecfdf5; }
.status-error { color: #be123c; background: #fff1f2; }
.status-running { color: #1d4ed8; background: #eff6ff; }
.status-paused { color: #92400e; background: #fef3c7; }
.status-pending { color: #64748b; background: #f8fafc; }
.status-dead-letter { color: #6d28d9; background: #f5f3ff; }
.status-cancelled { color: #64748b; background: #f1f5f9; }
.status-waiting { color: #b45309; background: #fffbeb; }

.run-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.run-actions button {
  min-height: 26px;
  padding: 0 8px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.run-actions button:hover {
  border-color: #bfdbfe;
  color: #1d4ed8;
  background: #eff6ff;
}

.run-actions button.danger:hover {
  border-color: #fecdd3;
  color: #be123c;
  background: #fff1f2;
}

.empty-hint {
  padding: 18px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .workflow-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .section-header,
  .workflow-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
