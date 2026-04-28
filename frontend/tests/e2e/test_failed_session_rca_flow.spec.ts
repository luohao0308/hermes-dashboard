import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SessionDetail from '@/components/SessionDetail.vue'

describe('failed session RCA flow', () => {
  it('opens a failed session, shows trace, and triggers RCA', async () => {
    const wrapper = mount(SessionDetail, {
      props: {
        taskId: 'failed-session-1',
        item: {
          task_id: 'failed-session-1',
          name: '失败 Session',
          completed_at: '2026-04-29T08:00:00Z',
          duration: 42,
          status: 'failed',
          input_tokens: 120,
          output_tokens: 20,
        },
        detail: {
          name: '失败 Session',
          status: 'failed',
          end_reason: 'tool_error',
          messages: [
            { role: 'user', content: '请读取日志', timestamp: '2026-04-29T08:00:00Z' },
            { role: 'assistant', content: '工具调用失败', timestamp: '2026-04-29T08:00:02Z' },
          ],
          message_count: 2,
          model: 'MiniMax',
          duration: 42,
          input_tokens: 120,
          output_tokens: 20,
        },
        logs: [
          {
            timestamp: '2026-04-29T08:00:01Z',
            type: 'error',
            message: 'failed-session-1 get_logs tool failed with timeout',
          },
        ],
        traceRun: {
          run_id: 'run-failed-1',
          session_id: 'chat-1',
          linked_session_id: 'failed-session-1',
          agent_id: 'Developer',
          status: 'error',
          started_at: '2026-04-29T08:00:00Z',
          completed_at: '2026-04-29T08:00:02Z',
        },
        traceSpans: [
          {
            span_id: 'span-tool-1',
            run_id: 'run-failed-1',
            span_type: 'tool',
            title: 'get_logs',
            summary: 'get_logs tool failed with timeout',
            agent_name: 'Developer',
            status: 'error',
            started_at: '2026-04-29T08:00:01Z',
            completed_at: '2026-04-29T08:00:02Z',
            metadata: {
              duration_ms: 1000,
              tool_name: 'get_logs',
              output_summary: 'timeout',
            },
          },
        ],
        rcaReport: null,
        runbookReport: null,
      },
    })

    expect(wrapper.text()).toContain('失败 Session')
    expect(wrapper.text()).toContain('失败')
    expect(wrapper.text()).toContain('Trace 时间线')
    expect(wrapper.text()).toContain('get_logs tool failed with timeout')
    expect(wrapper.text()).toContain('耗时 1000ms')

    await wrapper.find('.rca-panel .primary-btn').trigger('click')

    expect(wrapper.emitted('analyze-rca')).toHaveLength(1)
  })
})
