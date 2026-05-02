import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RunDetail from '@/components/RunDetail.vue'
import type { WorkflowRun, WorkflowSpan } from '@/types'

const mockRun: WorkflowRun = {
  id: 'run-12345678-abcd',
  runtime_id: 'rt-1',
  title: 'PR #42 code review',
  status: 'completed',
  input_summary: 'Review PR #42 for security issues',
  output_summary: 'No critical issues found',
  started_at: '2026-04-28T08:00:00Z',
  ended_at: '2026-04-28T08:05:00Z',
  duration_ms: 300000,
  total_tokens: 4200,
  total_cost: 0.0084,
  created_at: '2026-04-28T08:00:00Z',
  updated_at: '2026-04-28T08:05:00Z',
}

const mockSpans: WorkflowSpan[] = [
  {
    id: 'span-1',
    run_id: 'run-12345678-abcd',
    span_type: 'llm',
    title: 'Analyze code',
    status: 'completed',
    agent_name: 'Reviewer',
    model_name: 'claude-sonnet-4-6',
    input_tokens: 2000,
    output_tokens: 1200,
    cost: 0.006,
    started_at: '2026-04-28T08:00:30Z',
    ended_at: '2026-04-28T08:03:00Z',
    duration_ms: 150000,
    created_at: '2026-04-28T08:00:30Z',
  },
  {
    id: 'span-2',
    run_id: 'run-12345678-abcd',
    span_type: 'tool',
    title: 'Search codebase',
    status: 'completed',
    tool_name: 'grep',
    started_at: '2026-04-28T08:03:00Z',
    ended_at: '2026-04-28T08:03:05Z',
    duration_ms: 5000,
    created_at: '2026-04-28T08:03:00Z',
  },
]

describe('RunDetail', () => {
  it('renders run title and id', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    expect(wrapper.text()).toContain('PR #42 code review')
    expect(wrapper.text()).toContain('run-12345678-abcd')
    expect(wrapper.text()).toContain('Root Cause Analysis')
  })

  it('renders status', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    expect(wrapper.text()).toContain('completed')
  })

  it('renders duration and token summary', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    expect(wrapper.text()).toContain('4.2K')
    expect(wrapper.text()).toContain('$0.0084')
  })

  it('renders input and output summary', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    expect(wrapper.text()).toContain('Review PR #42 for security issues')
    expect(wrapper.text()).toContain('No critical issues found')
  })

  it('renders error summary when present', () => {
    const errorRun: WorkflowRun = { ...mockRun, status: 'error', error_summary: 'Connection timeout' }
    const wrapper = mount(RunDetail, {
      props: {
        runId: errorRun.id,
        run: errorRun,
        spans: [],
      },
    })

    expect(wrapper.text()).toContain('Connection timeout')
  })

  it('renders embedded TraceTimeline with spans', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    expect(wrapper.text()).toContain('Trace')
    expect(wrapper.text()).toContain('Analyze code')
    expect(wrapper.text()).toContain('Search codebase')
  })

  it('shows error box on error', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: 'run-bad',
        run: null,
        spans: [],
        error: 'Run not found',
      },
    })

    expect(wrapper.text()).toContain('Failed to load runs')
    expect(wrapper.text()).toContain('Run not found')
  })

  it('emits back event', async () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: mockRun.id,
        run: mockRun,
        spans: mockSpans,
      },
    })

    await wrapper.find('.back-btn').trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })

  it('shows loading state', () => {
    const wrapper = mount(RunDetail, {
      props: {
        runId: 'run-123',
        run: null,
        spans: [],
        loading: true,
      },
    })

    expect(wrapper.text()).toContain('Loading...')
  })
})
