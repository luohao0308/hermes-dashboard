import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowList from '@/components/WorkflowList.vue'
import WorkflowDetail from '@/components/WorkflowDetail.vue'
import WorkflowDefinitionEditor from '@/components/WorkflowDefinitionEditor.vue'
import HealthMatrix from '@/components/HealthMatrix.vue'
import type { WorkflowDefinition, WorkflowRunDetail } from '@/types'

const mockNodes = [
  {
    id: 'n-1',
    workflow_id: 'wf-1',
    node_id: 'fetch',
    title: 'Fetch Data',
    task_type: 'http',
    config: null,
    retry_policy: { max_retries: 3, backoff_seconds: 1.0 },
    timeout_seconds: 30,
    created_at: '2026-04-30T00:00:00Z',
  },
  {
    id: 'n-2',
    workflow_id: 'wf-1',
    node_id: 'process',
    title: 'Process Data',
    task_type: 'transform',
    config: null,
    retry_policy: { max_retries: 1, backoff_seconds: 2.0 },
    timeout_seconds: 60,
    created_at: '2026-04-30T00:00:00Z',
  },
  {
    id: 'n-3',
    workflow_id: 'wf-1',
    node_id: 'approve',
    title: 'Human Review',
    task_type: 'approval',
    config: null,
    retry_policy: null,
    timeout_seconds: null,
    created_at: '2026-04-30T00:00:00Z',
  },
]

const mockEdges = [
  { id: 'e-1', workflow_id: 'wf-1', from_node: 'fetch', to_node: 'process' },
  { id: 'e-2', workflow_id: 'wf-1', from_node: 'process', to_node: 'approve' },
]

const mockWorkflow: WorkflowDefinition = {
  id: 'wf-1',
  runtime_id: 'rt-1',
  name: 'Data Pipeline',
  description: 'Fetches, processes, and approves data',
  version: 1,
  created_at: '2026-04-30T00:00:00Z',
  updated_at: '2026-04-30T00:00:00Z',
  nodes: mockNodes,
  edges: mockEdges,
}

const mockWorkflowMinimal: WorkflowDefinition = {
  id: 'wf-2',
  runtime_id: 'rt-1',
  name: 'Simple Task',
  description: null,
  version: 2,
  created_at: '2026-04-29T00:00:00Z',
  updated_at: '2026-04-29T00:00:00Z',
  nodes: [mockNodes[0]],
  edges: [],
}

const mockTasks = [
  {
    id: 't-1',
    run_id: 'run-1',
    node_id: 'fetch',
    title: 'Fetch Data',
    status: 'completed',
    task_type: 'http',
    depends_on_json: null,
    started_at: '2026-04-30T10:00:00Z',
    ended_at: '2026-04-30T10:01:00Z',
    duration_ms: 60000,
    error_summary: null,
    retry_count: 0,
    metadata_json: null,
    created_at: '2026-04-30T10:00:00Z',
    updated_at: '2026-04-30T10:01:00Z',
  },
  {
    id: 't-2',
    run_id: 'run-1',
    node_id: 'process',
    title: 'Process Data',
    status: 'running',
    task_type: 'transform',
    depends_on_json: { depends_on: ['fetch'] },
    started_at: '2026-04-30T10:01:00Z',
    ended_at: null,
    duration_ms: null,
    error_summary: null,
    retry_count: 0,
    metadata_json: null,
    created_at: '2026-04-30T10:00:00Z',
    updated_at: '2026-04-30T10:01:00Z',
  },
  {
    id: 't-3',
    run_id: 'run-1',
    node_id: 'approve',
    title: 'Human Review',
    status: 'pending',
    task_type: 'approval',
    depends_on_json: { depends_on: ['process'] },
    started_at: null,
    ended_at: null,
    duration_ms: null,
    error_summary: null,
    retry_count: 0,
    metadata_json: null,
    created_at: '2026-04-30T10:00:00Z',
    updated_at: '2026-04-30T10:00:00Z',
  },
]

const mockRun: WorkflowRunDetail = {
  id: 'run-1',
  runtime_id: 'rt-1',
  workflow_id: 'wf-1',
  title: 'Data Pipeline Run #1',
  status: 'running',
  input_summary: 'batch-2026-04-30',
  output_summary: null,
  error_summary: null,
  started_at: '2026-04-30T10:00:00Z',
  ended_at: null,
  duration_ms: null,
  total_tokens: 1200,
  total_cost: 0.0042,
  metadata_json: null,
  created_at: '2026-04-30T10:00:00Z',
  updated_at: '2026-04-30T10:05:00Z',
  tasks: mockTasks,
}

const mockRunCompleted: WorkflowRunDetail = {
  ...mockRun,
  id: 'run-2',
  title: 'Data Pipeline Run #2',
  status: 'completed',
  ended_at: '2026-04-30T11:00:00Z',
  duration_ms: 3600000,
  tasks: mockTasks.map((t) => ({
    ...t,
    status: 'completed',
    ended_at: '2026-04-30T11:00:00Z',
    duration_ms: 3600000,
  })),
}

const mockRunPaused: WorkflowRunDetail = {
  ...mockRun,
  id: 'run-3',
  title: 'Data Pipeline Run #3',
  status: 'paused',
}

const mockRunFailed: WorkflowRunDetail = {
  ...mockRun,
  id: 'run-4',
  title: 'Data Pipeline Run #4',
  status: 'failed',
  error_summary: 'failed for retry test',
}

describe('WorkflowList', () => {
  it('renders loading state', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [], total: 0, limit: 20, offset: 0, loading: true },
    })
    expect(wrapper.text()).toContain('Loading workflows')
  })

  it('renders empty state', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [], total: 0, limit: 20, offset: 0, loading: false },
    })
    expect(wrapper.text()).toContain('No workflow definitions')
  })

  it('renders workflow cards', () => {
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [mockWorkflow, mockWorkflowMinimal],
        total: 2,
        limit: 20,
        offset: 0,
        loading: false,
      },
    })
    expect(wrapper.text()).toContain('Data Pipeline')
    expect(wrapper.text()).toContain('Simple Task')
    expect(wrapper.text()).toContain('v1')
    expect(wrapper.text()).toContain('v2')
  })

  it('shows node and edge counts', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 1, limit: 20, offset: 0, loading: false },
    })
    expect(wrapper.text()).toContain('3 Nodes')
    expect(wrapper.text()).toContain('2 Edges')
  })

  it('emits select when card clicked', async () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 1, limit: 20, offset: 0, loading: false },
    })
    await wrapper.find('.workflow-card').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual([mockWorkflow])
  })

  it('emits refresh when refresh button clicked', async () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [], total: 0, limit: 20, offset: 0, loading: false },
    })
    await wrapper.find('[data-test="refresh-workflows"]').trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })

  it('emits create when create button clicked', async () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [], total: 0, limit: 20, offset: 0, loading: false },
    })
    await wrapper.find('[data-test="create-workflow"]').trigger('click')
    expect(wrapper.emitted('create')).toBeTruthy()
  })

  it('emits edit without selecting workflow card', async () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 1, limit: 20, offset: 0, loading: false },
    })
    await wrapper.find('.card-action').trigger('click')
    expect(wrapper.emitted('edit')).toBeTruthy()
    expect(wrapper.emitted('edit')![0]).toEqual([mockWorkflow])
    expect(wrapper.emitted('select')).toBeFalsy()
  })

  it('shows pagination when total exceeds limit', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 50, limit: 20, offset: 0, loading: false },
    })
    expect(wrapper.text()).toContain('1-20 / 50')
  })

  it('disables prev button on first page', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 50, limit: 20, offset: 0, loading: false },
    })
    const buttons = wrapper.findAll('.pagination button')
    expect(buttons[0].attributes('disabled')).toBeDefined()
  })

  it('disables next button on last page', () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 50, limit: 20, offset: 40, loading: false },
    })
    const buttons = wrapper.findAll('.pagination button')
    expect(buttons[1].attributes('disabled')).toBeDefined()
  })

  it('emits pageChange on next click', async () => {
    const wrapper = mount(WorkflowList, {
      props: { workflows: [mockWorkflow], total: 50, limit: 20, offset: 0, loading: false },
    })
    const buttons = wrapper.findAll('.pagination button')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('pageChange')).toBeTruthy()
    expect(wrapper.emitted('pageChange')![0]).toEqual([20])
  })
})

describe('WorkflowDetail', () => {
  it('renders workflow name and version', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('Data Pipeline')
    expect(wrapper.text()).toContain('v1')
  })

  it('renders description when present', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('Fetches, processes, and approves data')
  })

  it('does not render description when null', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflowMinimal, runs: [], taskStatuses: {} },
    })
    expect(wrapper.find('.wf-desc').exists()).toBe(false)
  })

  it('renders nodes table', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('Nodes (3)')
    expect(wrapper.text()).toContain('fetch')
    expect(wrapper.text()).toContain('Fetch Data')
    expect(wrapper.text()).toContain('http')
    expect(wrapper.text()).toContain('30s')
  })

  it('shows retry policy in nodes table', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    const rows = wrapper.findAll('.data-table tbody tr')
    expect(rows[0].text()).toContain('3')
    expect(rows[1].text()).toContain('1')
  })

  it('shows dash for nodes without timeout', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    const rows = wrapper.findAll('.data-table tbody tr')
    expect(rows[2].text()).toContain('-')
  })

  it('renders empty runs hint', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('No runs found')
  })

  it('renders runs table with data', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [mockRun, mockRunCompleted], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('run-1'.slice(0, 8))
    expect(wrapper.text()).toContain('running')
    expect(wrapper.text()).toContain('completed')
  })

  it('renders run control actions by status', () => {
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow: mockWorkflow,
        runs: [mockRun, mockRunPaused, mockRunFailed, mockRunCompleted],
        taskStatuses: {},
      },
    })
    expect(wrapper.text()).toContain('Pause')
    expect(wrapper.text()).toContain('Resume')
    expect(wrapper.text()).toContain('Retry')
    expect(wrapper.text()).toContain('Cancel')
  })

  it('does not show retry for paused runs', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [mockRunPaused], taskStatuses: {} },
    })
    const actionText = wrapper.find('.run-actions').text()

    expect(actionText).toContain('Resume')
    expect(actionText).toContain('Cancel')
    expect(actionText).not.toContain('Retry')
  })

  it('emits run control events without selecting the row', async () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [mockRun], taskStatuses: {} },
    })

    await wrapper.find('.run-actions button').trigger('click')

    expect(wrapper.emitted('pauseRun')).toBeTruthy()
    expect(wrapper.emitted('pauseRun')![0]).toEqual([mockRun])
    expect(wrapper.emitted('selectRun')).toBeFalsy()
  })

  it('shows duration for completed runs', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [mockRunCompleted], taskStatuses: {} },
    })
    expect(wrapper.text()).toContain('60.0m')
  })

  it('renders selected run task observability', () => {
    const observableRun: WorkflowRunDetail = {
      ...mockRun,
      tasks: mockRun.tasks.map((task, idx) => ({
        ...task,
        locked_by: idx === 1 ? 'worker-alpha' : null,
        locked_at: idx === 1 ? '2026-04-30T10:02:00Z' : null,
        next_retry_at: idx === 2 ? '2026-04-30T10:03:00Z' : null,
        error_summary: idx === 2 ? 'waiting on upstream' : null,
      })),
    }
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [observableRun], selectedRun: observableRun, taskStatuses: {} },
    })

    expect(wrapper.text()).toContain('Run Tasks')
    expect(wrapper.text()).toContain('worker-alpha')
    expect(wrapper.text()).toContain('waiting on upstream')
  })

  it('emits back when back button clicked', async () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    await wrapper.find('.btn-ghost').trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })

  it('emits startRun when start run button clicked', async () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    await wrapper.find('.btn-primary').trigger('click')
    expect(wrapper.emitted('startRun')).toBeTruthy()
  })

  it('emits selectRun when run row clicked', async () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [mockRun], taskStatuses: {} },
    })
    await wrapper.find('.clickable').trigger('click')
    expect(wrapper.emitted('selectRun')).toBeTruthy()
    expect(wrapper.emitted('selectRun')![0]).toEqual([mockRun])
  })

  it('renders SVG DAG graph', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.find('.dag-svg').exists()).toBe(true)
    expect(wrapper.findAll('.dag-node')).toHaveLength(3)
    expect(wrapper.findAll('.dag-edge')).toHaveLength(2)
  })

  it('applies status classes to DAG nodes', () => {
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow: mockWorkflow,
        runs: [],
        taskStatuses: { fetch: 'completed', process: 'running' },
      },
    })
    const nodes = wrapper.findAll('.dag-node')
    expect(nodes[0].classes()).toContain('status-completed')
    expect(nodes[1].classes()).toContain('status-running')
    expect(nodes[2].classes()).not.toContain('status-completed')
  })

  it('applies failed status class to DAG nodes', () => {
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow: mockWorkflow,
        runs: [],
        taskStatuses: { fetch: 'failed' },
      },
    })
    const nodes = wrapper.findAll('.dag-node')
    expect(nodes[0].classes()).toContain('status-failed')
  })

  it('renders DAG node labels and types', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    const labels = wrapper.findAll('.dag-node-label')
    expect(labels).toHaveLength(3)
    expect(labels[0].text()).toBe('Fetch Data')
    expect(labels[1].text()).toBe('Process Data')

    const types = wrapper.findAll('.dag-node-type')
    expect(types[0].text()).toBe('http')
    expect(types[1].text()).toBe('transform')
  })

  it('renders edges between nodes', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflow, runs: [], taskStatuses: {} },
    })
    expect(wrapper.findAll('.dag-edge')).toHaveLength(2)
    expect(wrapper.findAll('.dag-arrow')).toHaveLength(2)
  })

  it('handles single-node workflow DAG', () => {
    const wrapper = mount(WorkflowDetail, {
      props: { workflow: mockWorkflowMinimal, runs: [], taskStatuses: {} },
    })
    expect(wrapper.findAll('.dag-node')).toHaveLength(1)
    expect(wrapper.findAll('.dag-edge')).toHaveLength(0)
  })
})

describe('WorkflowDefinitionEditor', () => {
  const validJson = JSON.stringify({
    name: 'Editor Test',
    runtime_id: 'rt-1',
    nodes: [{ node_id: 'a', title: 'A' }],
    edges: [],
  }, null, 2)

  it('emits parsed workflow JSON on save', async () => {
    const wrapper = mount(WorkflowDefinitionEditor, {
      props: {
        open: true,
        mode: 'create',
        initialJson: validJson,
        sampleJson: validJson,
      },
    })

    await wrapper.find('.btn-primary').trigger('click')

    expect(wrapper.emitted('save')).toBeTruthy()
    expect(wrapper.emitted('save')![0][0]).toMatchObject({ name: 'Editor Test', runtime_id: 'rt-1' })
  })

  it('shows validation error for invalid JSON', async () => {
    const wrapper = mount(WorkflowDefinitionEditor, {
      props: {
        open: true,
        mode: 'create',
        initialJson: '{',
        sampleJson: validJson,
      },
    })

    await wrapper.find('.btn-primary').trigger('click')

    expect(wrapper.text()).toContain('Invalid JSON')
    expect(wrapper.emitted('save')).toBeFalsy()
  })

  it('loads sample JSON', async () => {
    const wrapper = mount(WorkflowDefinitionEditor, {
      props: {
        open: true,
        mode: 'create',
        initialJson: '{"name":"empty"}',
        sampleJson: validJson,
      },
    })

    await wrapper.find('.editor-actions .btn').trigger('click')

    expect((wrapper.find('textarea').element as HTMLTextAreaElement).value).toContain('Editor Test')
  })
})

describe('HealthMatrix', () => {
  it('renders worker heartbeat metadata', () => {
    const wrapper = mount(HealthMatrix, {
      props: {
        loading: false,
        health: {
          status: 'healthy',
          version: '3.0.0',
          active_connections: 1,
          database: { status: 'connected', migration_version: 'abcdef123456' },
          workers: {
            'scheduler-worker': {
              status: 'alive',
              last_seen_seconds_ago: 5,
              worker_id: 'worker-alpha',
              pid: 123,
              version: '3.0.0',
            },
          },
        },
        metrics: {
          workers: {
            scheduler_worker: {
              status: 'alive',
              age_seconds: 5,
              worker_id: 'worker-alpha',
              pid: 123,
            },
          },
        },
      },
    })

    expect(wrapper.text()).toContain('worker-alpha')
    expect(wrapper.text()).toContain('pid 123')
  })
})
