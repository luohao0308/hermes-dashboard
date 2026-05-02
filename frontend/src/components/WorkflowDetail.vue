<template>
  <div class="workflow-detail">
    <div class="section-header">
      <button class="btn btn-ghost" @click="$emit('back')">{{ t('common.back') }}</button>
      <h2 class="section-title">{{ workflow.name }}</h2>
      <span class="card-badge">v{{ workflow.version }}</span>
    </div>

    <p v-if="workflow.description" class="wf-desc">{{ workflow.description }}</p>

    <!-- DAG Graph -->
    <div class="dag-section">
      <h3 class="sub-title">{{ t('workflows.dag') }}</h3>
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
          <g
            v-for="node in layoutNodes"
            :key="node.node_id"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect
              :width="NODE_W"
              :height="NODE_H"
              rx="8"
              class="dag-node"
              :class="nodeStatusClass(node.node_id)"
            />
            <text
              :x="NODE_W / 2"
              :y="NODE_H / 2 - 6"
              text-anchor="middle"
              class="dag-node-label"
            >
              {{ node.title }}
            </text>
            <text
              :x="NODE_W / 2"
              :y="NODE_H / 2 + 10"
              text-anchor="middle"
              class="dag-node-type"
            >
              {{ node.task_type }}
            </text>
          </g>
        </svg>
      </div>
    </div>

    <!-- Nodes Table -->
    <div class="nodes-section">
      <h3 class="sub-title">{{ t('workflows.nodes') }} ({{ workflow.nodes.length }})</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('workflows.nodes') }} ID</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('runAnalysis.steps') }}</th>
            <th>{{ t('common.status') }}</th>
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

    <!-- Version History -->
    <div class="versions-section">
      <div class="versions-header">
        <h3 class="sub-title">{{ t('workflows.versions') }}</h3>
        <button class="btn btn-ghost" @click="$emit('loadVersions')" :disabled="loadingVersions">
          {{ loadingVersions ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
      <div v-if="!versions || versions.length === 0" class="empty-hint">{{ t('workflows.noVersions') }}</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>{{ t('workflows.version') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.time') }}</th>
            <th>{{ t('audit.actor') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in versions" :key="v.id">
            <td class="mono">v{{ v.version }}</td>
            <td>{{ v.name }}</td>
            <td>{{ formatTime(v.created_at) }}</td>
            <td>{{ v.created_by || '-' }}</td>
            <td>
              <button
                class="btn btn-ghost rollback-btn"
                @click="$emit('rollback', v.version)"
                :disabled="rollingBack"
              >
                {{ t('workflows.rollback') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Runs -->
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
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.id"
            class="clickable"
            @click="$emit('selectRun', run)"
          >
            <td class="mono">{{ run.id.slice(0, 8) }}</td>
            <td>
              <span :class="['status-chip', statusClass(run.status)]">{{ run.status }}</span>
            </td>
            <td>{{ run.tasks.length }}</td>
            <td>{{ run.started_at ? formatTime(run.started_at) : '-' }}</td>
            <td>{{ run.duration_ms ? formatDuration(run.duration_ms) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WorkflowDefinition, WorkflowRunDetail, WorkflowVersionHistoryItem } from '../types'

const { t } = useI18n()

const props = defineProps<{
  workflow: WorkflowDefinition
  runs: WorkflowRunDetail[]
  taskStatuses?: Record<string, string>
  versions?: WorkflowVersionHistoryItem[]
  loadingVersions?: boolean
  rollingBack?: boolean
}>()

defineEmits<{
  back: []
  startRun: []
  selectRun: [run: WorkflowRunDetail]
  loadVersions: []
  rollback: [version: number]
}>()

const NODE_W = 160
const NODE_H = 56
const GAP_X = 60
const GAP_Y = 40

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
      if (inDegree[next] === 0) {
        queue.push(next)
      }
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
        x: lv * (NODE_W + GAP_X),
        y: col * (NODE_H + GAP_Y),
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

const svgViewBox = computed(() => {
  if (layoutNodes.value.length === 0) return '0 0 200 100'
  const maxX = Math.max(...layoutNodes.value.map((n) => n.x + NODE_W)) + 20
  const maxY = Math.max(...layoutNodes.value.map((n) => n.y + NODE_H)) + 20
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
  const status = props.taskStatuses?.[nodeId]
  if (!status) return ''
  return `status-${status}`
}

function statusClass(status: string): string {
  if (status === 'completed') return 'status-success'
  if (status === 'failed') return 'status-error'
  if (status === 'running') return 'status-running'
  if (status === 'dead_letter') return 'status-dead-letter'
  if (status === 'cancelled') return 'status-cancelled'
  if (status === 'waiting_approval') return 'status-waiting'
  return 'status-pending'
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
  gap: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.sub-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.wf-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.btn {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  transition: all 0.2s;
}

.btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-ghost {
  background: transparent;
  border-color: transparent;
}

.btn-primary {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.card-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent-color);
  font-weight: 600;
}

.dag-section {
  background: var(--glass-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.dag-container {
  overflow-x: auto;
  margin-top: 12px;
}

.dag-svg {
  min-width: 400px;
  min-height: 200px;
}

.dag-edge {
  stroke: var(--border-subtle);
  stroke-width: 2;
}

.dag-arrow {
  fill: var(--border-subtle);
}

.dag-node {
  fill: var(--bg-tertiary);
  stroke: var(--border-subtle);
  stroke-width: 1.5;
}

.dag-node.status-completed {
  fill: #16a34a22;
  stroke: #16a34a;
}

.dag-node.status-running {
  fill: #2563eb22;
  stroke: #2563eb;
}

.dag-node.status-failed {
  fill: #dc262622;
  stroke: #dc2626;
}

.dag-node.status-dead_letter {
  fill: #7c3aed22;
  stroke: #7c3aed;
}

.dag-node.status-cancelled {
  fill: #6b728022;
  stroke: #6b7280;
}

.dag-node.status-waiting_approval {
  fill: #f59e0b22;
  stroke: #f59e0b;
}

.dag-node-label {
  fill: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.dag-node-type {
  fill: var(--text-muted);
  font-size: 11px;
}

.nodes-section,
.runs-section,
.versions-section {
  background: var(--glass-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.runs-header,
.versions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rollback-btn {
  font-size: 11px;
  padding: 4px 10px;
  color: var(--accent-color);
  border-color: var(--accent-color);
}

.rollback-btn:hover:not(:disabled) {
  background: var(--accent-soft);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  padding: 8px 12px;
  color: var(--text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border-subtle);
}

.data-table td {
  padding: 8px 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table .clickable {
  cursor: pointer;
}

.data-table .clickable:hover td {
  background: var(--bg-tertiary);
}

.mono {
  font-family: monospace;
  font-size: 12px;
}

.status-chip {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.status-chip.status-success {
  background: #16a34a22;
  color: #16a34a;
}

.status-chip.status-error {
  background: #dc262622;
  color: #dc2626;
}

.status-chip.status-running {
  background: #2563eb22;
  color: #2563eb;
}

.status-chip.status-pending {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.status-chip.status-dead-letter {
  background: #7c3aed22;
  color: #7c3aed;
}

.status-chip.status-cancelled {
  background: #6b728022;
  color: #6b7280;
}

.status-chip.status-waiting {
  background: #f59e0b22;
  color: #f59e0b;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-muted);
  padding: 16px 0;
}
</style>
