import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TraceTimeline from '@/components/TraceTimeline.vue'

describe('TraceTimeline', () => {
  it('renders run status and spans', () => {
    const wrapper = mount(TraceTimeline, {
      props: {
        run: {
          run_id: 'run-12345678',
          session_id: 'session-1',
          agent_id: 'Developer',
          status: 'completed',
          started_at: '2026-04-28T08:00:00Z',
        },
        spans: [
          {
            span_id: 'span-1',
            run_id: 'run-12345678',
            span_type: 'handoff',
            title: 'Agent handoff',
            summary: 'handoff to Reviewer',
            agent_name: 'Developer',
            status: 'completed',
            started_at: '2026-04-28T08:00:00Z',
            metadata: {
              duration_ms: 120,
              handoff: {
                reason: '需要 Reviewer 审查',
                priority: 'normal',
                expected_output: '审查结论',
              },
            },
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('Trace 时间线')
    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('Agent handoff')
    expect(wrapper.text()).toContain('handoff to Reviewer')
    expect(wrapper.text()).toContain('耗时 120ms')
    expect(wrapper.text()).toContain('需要 Reviewer 审查')
    expect(wrapper.text()).toContain('审查结论')
  })

  it('renders empty state', () => {
    const wrapper = mount(TraceTimeline, {
      props: {
        run: null,
        spans: [],
      },
    })

    expect(wrapper.text()).toContain('暂无 trace 数据')
  })
})
