import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowDetail from '@/components/WorkflowDetail.vue'
import type { WorkflowDefinition, WorkflowRunDetail } from '@/types'

function createMockWorkflow(overrides: Partial<WorkflowDefinition> = {}): WorkflowDefinition {
  return {
    id: '123e4567-e89b-12d3-a456-426614174000',
    runtime_id: '223e4567-e89b-12d3-a456-426614174001',
    name: 'Test Workflow',
    description: 'A test workflow',
    version: 1,
    timeout_seconds: null,
    max_concurrent_tasks: null,
    is_reusable: false,
    created_at: '2026-05-12T12:00:00Z',
    updated_at: '2026-05-12T12:00:00Z',
    nodes: [
      { id: 'n1', workflow_id: '123', node_id: 'start', title: 'Start', task_type: 'action', created_at: '2026-05-12T12:00:00Z' },
      { id: 'n2', workflow_id: '123', node_id: 'sub', title: 'Call Child', task_type: 'subworkflow', child_workflow_id: '323e4567-e89b-12d3-a456-426614174002', created_at: '2026-05-12T12:00:00Z' },
      { id: 'n3', workflow_id: '123', node_id: 'end', title: 'End', task_type: 'action', created_at: '2026-05-12T12:00:00Z' },
    ],
    edges: [
      { id: 'e1', workflow_id: '123', from_node: 'start', to_node: 'sub' },
      { id: 'e2', workflow_id: '123', from_node: 'sub', to_node: 'end' },
    ],
    ...overrides,
  }
}

function createMockRun(overrides: Partial<WorkflowRunDetail> = {}): WorkflowRunDetail {
  return {
    id: 'abc12345-e89b-12d3-a456-426614174000',
    runtime_id: '223e4567-e89b-12d3-a456-426614174001',
    workflow_id: '123e4567-e89b-12d3-a456-426614174000',
    title: 'Test Run',
    status: 'running',
    input_summary: null,
    output_summary: null,
    error_summary: null,
    started_at: '2026-05-12T12:00:00Z',
    ended_at: null,
    duration_ms: null,
    total_tokens: null,
    total_cost: null,
    metadata_json: null,
    created_at: '2026-05-12T12:00:00Z',
    updated_at: '2026-05-12T12:00:00Z',
    tasks: [],
    ...overrides,
  }
}

describe('WorkflowDetail', () => {
  it('renders DAG with subworkflow nodes', () => {
    const workflow = createMockWorkflow()
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    // Check that subworkflow node is rendered with indicator
    const svg = wrapper.find('.dag-svg')
    expect(svg.exists()).toBe(true)

    // Find subworkflow indicator
    const subIndicator = wrapper.find('.subworkflow-indicator')
    expect(subIndicator.exists()).toBe(true)
    expect(subIndicator.text()).toBe('↗')
  })

  it('renders node task_type labels', () => {
    const workflow = createMockWorkflow()
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    const nodeTypes = wrapper.findAll('.dag-node-type')
    const typeTexts = nodeTypes.map(n => n.text())

    expect(typeTexts).toContain('action')
    expect(typeTexts).toContain('subworkflow')
  })

  it('emits drillDown when subworkflow node with child_run_id is clicked', async () => {
    const workflow = createMockWorkflow()
    const childRunId = 'def45678-e89b-12d3-a456-426614174003'

    const run = createMockRun({
      tasks: [
        {
          id: 't1',
          run_id: 'abc12345',
          node_id: 'start',
          title: 'Start',
          status: 'completed',
          task_type: 'action',
          retry_count: 0,
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
        {
          id: 't2',
          run_id: 'abc12345',
          node_id: 'sub',
          title: 'Call Child',
          status: 'running',
          task_type: 'subworkflow',
          retry_count: 0,
          metadata_json: { child_run_id: childRunId },
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
      ],
    })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
        selectedRun: run,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    // Find the clickable subworkflow node
    const clickableNodes = wrapper.findAll('.clickable-node')
    expect(clickableNodes.length).toBe(1)

    await clickableNodes[0].trigger('click')

    expect(wrapper.emitted('drillDown')).toHaveLength(1)
    expect(wrapper.emitted('drillDown')![0]).toEqual([childRunId])
  })

  it('does not emit drillDown when subworkflow node has no child_run_id', async () => {
    const workflow = createMockWorkflow()
    const run = createMockRun({
      tasks: [
        {
          id: 't1',
          run_id: 'abc12345',
          node_id: 'sub',
          title: 'Call Child',
          status: 'pending',
          task_type: 'subworkflow',
          retry_count: 0,
          metadata_json: null,
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
      ],
    })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
        selectedRun: run,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    // No clickable nodes should exist when child_run_id is missing
    const clickableNodes = wrapper.findAll('.clickable-node')
    expect(clickableNodes.length).toBe(0)
  })

  it('shows task status colors in DAG', () => {
    const workflow = createMockWorkflow()
    const run = createMockRun({
      tasks: [
        {
          id: 't1',
          run_id: 'abc12345',
          node_id: 'start',
          title: 'Start',
          status: 'completed',
          task_type: 'action',
          retry_count: 0,
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
        {
          id: 't2',
          run_id: 'abc12345',
          node_id: 'sub',
          title: 'Call Child',
          status: 'running',
          task_type: 'subworkflow',
          retry_count: 0,
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
      ],
    })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
        selectedRun: run,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    const nodes = wrapper.findAll('.dag-node')
    const statusClasses = nodes.map(n => n.classes().filter(c => c.startsWith('status-')))

    // Should have status classes based on task status
    const hasStatusClasses = statusClasses.some(classes => classes.length > 0)
    expect(hasStatusClasses).toBe(true)
  })

  it('renders runs table with run controls', () => {
    const workflow = createMockWorkflow()
    const run = createMockRun({
      status: 'running',
      tasks: [
        {
          id: 't1',
          run_id: 'abc12345',
          node_id: 'start',
          title: 'Start',
          status: 'running',
          task_type: 'action',
          retry_count: 0,
          created_at: '2026-05-12T12:00:00Z',
          updated_at: '2026-05-12T12:00:00Z',
        },
      ],
    })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    expect(wrapper.text()).toContain('running')
    expect(wrapper.find('.status-running').exists()).toBe(true)

    // Should have pause button for running run
    const pauseBtn = wrapper.find('.run-actions button')
    expect(pauseBtn.exists()).toBe(true)
    expect(pauseBtn.text()).toContain('Pause')
  })

  it('emits pauseRun when pause clicked', async () => {
    const workflow = createMockWorkflow()
    const run = createMockRun({ status: 'running' })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    await wrapper.find('.run-actions button').trigger('click')

    expect(wrapper.emitted('pauseRun')).toHaveLength(1)
    expect(wrapper.emitted('pauseRun')![0]).toEqual([run])
  })

  it('emits resumeRun when resume clicked on paused run', async () => {
    const workflow = createMockWorkflow()
    const run = createMockRun({ status: 'paused' })

    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [run],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    await wrapper.find('.run-actions button').trigger('click')

    expect(wrapper.emitted('resumeRun')).toHaveLength(1)
    expect(wrapper.emitted('resumeRun')![0]).toEqual([run])
  })

  it('shows node table with child_workflow_id for subworkflow nodes', () => {
    const workflow = createMockWorkflow()
    const wrapper = mount(WorkflowDetail, {
      props: {
        workflow,
        runs: [],
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
        },
      },
    })

    const table = wrapper.find('.data-table')
    expect(table.exists()).toBe(true)

    // Should show task_type column
    expect(table.text()).toContain('subworkflow')
  })
})
