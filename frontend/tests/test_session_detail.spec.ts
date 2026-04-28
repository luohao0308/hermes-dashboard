import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SessionDetail from '@/components/SessionDetail.vue'

describe('SessionDetail', () => {
  it('renders session summary and messages', () => {
    const wrapper = mount(SessionDetail, {
      props: {
        taskId: 'session-12345678',
        item: {
          task_id: 'session-12345678',
          name: '复盘测试',
          completed_at: '2026-04-28T08:00:00Z',
          duration: 125,
          status: 'success',
          input_tokens: 100,
          output_tokens: 50,
        },
        detail: {
          name: '复盘测试',
          status: 'completed',
          messages: [
            { role: 'user', content: '请分析问题', timestamp: '2026-04-28T08:00:00Z' },
            { role: 'assistant', content: '分析完成', timestamp: '2026-04-28T08:01:00Z' },
          ],
          message_count: 2,
          model: 'MiniMax',
          duration: 125,
          input_tokens: 100,
          output_tokens: 50,
        },
        logs: [],
        traceRun: null,
        traceSpans: [],
      },
    })

    expect(wrapper.text()).toContain('复盘测试')
    expect(wrapper.text()).toContain('2m 5s')
    expect(wrapper.text()).toContain('150')
    expect(wrapper.text()).toContain('请分析问题')
    expect(wrapper.text()).toContain('未发现明显失败信号')
  })

  it('detects error signals from related logs', () => {
    const wrapper = mount(SessionDetail, {
      props: {
        taskId: 'abc123456789',
        item: null,
        detail: {
          status: 'completed',
          messages: [{ role: 'assistant', content: 'done' }],
        },
        logs: [
          {
            timestamp: '2026-04-28T08:00:00Z',
            type: 'error',
            message: 'abc12345 tool failed with timeout',
          },
        ],
        traceRun: null,
        traceSpans: [],
      },
    })

    expect(wrapper.text()).toContain('发现错误信号')
    expect(wrapper.text()).toContain('tool failed with timeout')
  })

  it('emits back and refresh actions', async () => {
    const wrapper = mount(SessionDetail, {
      props: {
        taskId: 'session-1',
        item: null,
        detail: null,
        logs: [],
        traceRun: {
          run_id: 'run-12345678',
          session_id: 'session-1',
          agent_id: 'Developer',
          status: 'completed',
          started_at: '2026-04-28T08:00:00Z',
        },
        traceSpans: [
          {
            span_id: 'span-1',
            run_id: 'run-12345678',
            span_type: 'user_input',
            title: 'User message',
            summary: 'hello',
            status: 'completed',
            started_at: '2026-04-28T08:00:00Z',
          },
        ],
      },
    })

    await wrapper.find('.back-btn').trigger('click')
    await wrapper.find('.refresh-btn').trigger('click')

    expect(wrapper.emitted('back')).toHaveLength(1)
    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })
})
