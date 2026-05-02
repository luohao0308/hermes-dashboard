import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RunList from '@/components/RunList.vue'
import type { WorkflowRun, WorkflowRuntime } from '@/types'

const mockRuntimes: WorkflowRuntime[] = [
  { id: 'rt-1', name: 'CI Pipeline', type: 'github_actions', status: 'active', created_at: '2026-04-01T00:00:00Z', updated_at: '2026-04-01T00:00:00Z' },
  { id: 'rt-2', name: 'Code Review', type: 'custom', status: 'active', created_at: '2026-04-01T00:00:00Z', updated_at: '2026-04-01T00:00:00Z' },
]

const mockRuns: WorkflowRun[] = [
  {
    id: 'run-aaa',
    runtime_id: 'rt-1',
    title: 'PR #42 review',
    status: 'completed',
    started_at: '2026-04-28T08:00:00Z',
    ended_at: '2026-04-28T08:05:00Z',
    duration_ms: 300000,
    total_tokens: 1500,
    total_cost: 0.003,
    created_at: '2026-04-28T08:00:00Z',
    updated_at: '2026-04-28T08:05:00Z',
  },
  {
    id: 'run-bbb',
    runtime_id: 'rt-2',
    title: 'Bug triage',
    status: 'running',
    started_at: '2026-04-28T09:00:00Z',
    created_at: '2026-04-28T09:00:00Z',
    updated_at: '2026-04-28T09:00:00Z',
  },
  {
    id: 'run-ccc',
    runtime_id: 'rt-1',
    title: 'Deploy check',
    status: 'error',
    error_summary: 'Timeout',
    started_at: '2026-04-28T10:00:00Z',
    ended_at: '2026-04-28T10:01:00Z',
    duration_ms: 60000,
    created_at: '2026-04-28T10:00:00Z',
    updated_at: '2026-04-28T10:01:00Z',
  },
]

describe('RunList', () => {
  it('renders run titles and status icons', () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns,
        runtimes: mockRuntimes,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('PR #42 review')
    expect(wrapper.text()).toContain('Bug triage')
    expect(wrapper.text()).toContain('Deploy check')
    expect(wrapper.text()).toContain('3 runs')
  })

  it('renders duration and token info', () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns,
        runtimes: mockRuntimes,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('1.5K tokens')
  })

  it('shows empty state when no runs', () => {
    const wrapper = mount(RunList, {
      props: {
        runs: [],
        runtimes: mockRuntimes,
        total: 0,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('No runs found')
  })

  it('emits selectRun on click', async () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns,
        runtimes: mockRuntimes,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    await wrapper.findAll('.run-item')[0].trigger('click')
    expect(wrapper.emitted('selectRun')).toBeTruthy()
    expect(wrapper.emitted('selectRun')![0]).toEqual(['run-aaa'])
  })

  it('emits filterChange when status filter changes', async () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns,
        runtimes: mockRuntimes,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    const selects = wrapper.findAll('.filter-select')
    await selects[0].setValue('completed')
    expect(wrapper.emitted('filterChange')).toBeTruthy()
    expect(wrapper.emitted('filterChange')![0]).toEqual([{ status: 'completed', runtime_id: '', connector_type: '' }])
  })

  it('shows pagination when total exceeds limit', () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns.slice(0, 2),
        runtimes: mockRuntimes,
        total: 10,
        limit: 2,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('1–2 of 10')
    expect(wrapper.find('.pagination').exists()).toBe(true)
  })

  it('emits pageChange on pagination click', async () => {
    const wrapper = mount(RunList, {
      props: {
        runs: mockRuns.slice(0, 2),
        runtimes: mockRuntimes,
        total: 10,
        limit: 2,
        offset: 0,
      },
    })

    const nextBtn = wrapper.findAll('.page-btn')[1]
    await nextBtn.trigger('click')
    expect(wrapper.emitted('pageChange')).toBeTruthy()
    expect(wrapper.emitted('pageChange')![0]).toEqual([2])
  })

  it('shows loading skeleton', () => {
    const wrapper = mount(RunList, {
      props: {
        runs: [],
        runtimes: mockRuntimes,
        total: 0,
        limit: 50,
        offset: 0,
        loading: true,
      },
    })

    expect(wrapper.find('.state-loading').exists()).toBe(true)
  })
})
