import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowList from '@/components/WorkflowList.vue'
import type { WorkflowDefinition } from '@/types'

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
    nodes: [],
    edges: [],
    ...overrides,
  }
}

describe('WorkflowList', () => {
  it('renders workflow cards with correct metadata', () => {
    const workflows = [
      createMockWorkflow({
        id: '111e4567-e89b-12d3-a456-426614174000',
        name: 'Workflow One',
        nodes: [
          { id: 'n1', workflow_id: '111', node_id: 'a', title: 'A', task_type: 'action', created_at: '2026-05-12T12:00:00Z' },
        ],
        edges: [],
      }),
      createMockWorkflow({
        id: '222e4567-e89b-12d3-a456-426614174001',
        name: 'Workflow Two',
        nodes: [
          { id: 'n2', workflow_id: '222', node_id: 'b', title: 'B', task_type: 'action', created_at: '2026-05-12T12:00:00Z' },
          { id: 'n3', workflow_id: '222', node_id: 'c', title: 'C', task_type: 'action', created_at: '2026-05-12T12:00:00Z' },
        ],
        edges: [
          { id: 'e1', workflow_id: '222', from_node: 'b', to_node: 'c' },
        ],
      }),
    ]

    const wrapper = mount(WorkflowList, {
      props: {
        workflows,
        total: 2,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    expect(wrapper.text()).toContain('Workflow One')
    expect(wrapper.text()).toContain('Workflow Two')
    expect(wrapper.text()).toContain('1 Nodes')
    expect(wrapper.text()).toContain('2 Nodes')
  })

  it('highlights reusable workflows with badge', () => {
    const workflows = [
      createMockWorkflow({
        name: 'Reusable WF',
        is_reusable: true,
      }),
      createMockWorkflow({
        name: 'Regular WF',
        is_reusable: false,
      }),
    ]

    const wrapper = mount(WorkflowList, {
      props: {
        workflows,
        total: 2,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    const reusableBadge = wrapper.find('.reusable-badge')
    expect(reusableBadge.exists()).toBe(true)
    expect(reusableBadge.text()).toBe('Reusable')

    const reusableCard = wrapper.find('.reusable-card')
    expect(reusableCard.exists()).toBe(true)
  })

  it('filters by reusable toggle', async () => {
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [],
        total: 0,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    const checkbox = wrapper.find('.filter-toggle input[type="checkbox"]')
    await checkbox.setValue(true)

    expect(wrapper.emitted('filterChange')).toHaveLength(1)
    expect(wrapper.emitted('filterChange')![0]).toEqual([true])
  })

  it('emits select event when workflow card clicked', async () => {
    const workflow = createMockWorkflow()
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [workflow],
        total: 1,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    await wrapper.find('.workflow-card').trigger('click')

    expect(wrapper.emitted('select')).toHaveLength(1)
    expect(wrapper.emitted('select')![0]).toEqual([workflow])
  })

  it('emits edit event when edit button clicked', async () => {
    const workflow = createMockWorkflow()
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [workflow],
        total: 1,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    await wrapper.find('.card-action').trigger('click')

    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('edit')![0]).toEqual([workflow])
  })

  it('shows empty state when no workflows', () => {
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [],
        total: 0,
        limit: 10,
        offset: 0,
        loading: false,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div>Loading...</div>' },
          EmptyState: { template: '<div class="empty-state">No workflows</div>' },
        },
      },
    })

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No workflows')
  })

  it('shows loading state when loading', () => {
    const wrapper = mount(WorkflowList, {
      props: {
        workflows: [],
        total: 0,
        limit: 10,
        offset: 0,
        loading: true,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div class="loading-state">Loading...</div>' },
          EmptyState: { template: '<div>Empty</div>' },
        },
      },
    })

    expect(wrapper.find('.loading-state').exists()).toBe(true)
  })
})
