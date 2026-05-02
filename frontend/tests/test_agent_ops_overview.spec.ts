import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentOpsOverview from '@/components/AgentOpsOverview.vue'

describe('AgentOpsOverview', () => {
  it('renders healthy overview metrics', () => {
    const wrapper = mount(AgentOpsOverview, {
      props: {
        status: { gateway_running: true, version: '1.0.0' },
        isConnected: true,
        tasks: [{ task_id: '1', status: 'running', message_count: 8 }],
        logs: [{ type: 'info' }],
        history: [{ input_tokens: 100, output_tokens: 50 }],
        snapshot: {
          health: { service: 'ai-workflow-control-plane', status: 'healthy', database: { status: 'connected', migration_version: '009' } },
          analytics: { workers: { 'scheduler-worker': { status: 'alive' } }, approvals: { pending: 0 } },
          evalSummary: { success_rate: 0.75, total_runs: 4, error_runs: 1 },
          modelInfo: { model: 'MiniMax-M2.7-highspeed', provider: 'MiniMax' },
        },
      },
    })

    expect(wrapper.text()).toContain('AgentOps 概览')
    expect(wrapper.text()).toContain('稳定')
    expect(wrapper.text()).toContain('MiniMax-M2.7-highspeed')
    expect(wrapper.text()).toContain('1 active signals')
    expect(wrapper.text()).toContain('75%')
    expect(wrapper.text()).toContain('4 runs / 1 errors')
  })

  it('emits refresh when sync button is clicked', async () => {
    const wrapper = mount(AgentOpsOverview, {
      props: {
        status: null,
        isConnected: false,
        tasks: [],
        logs: [],
        history: [],
        snapshot: {},
      },
    })

    await wrapper.find('.overview-refresh').trigger('click')

    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })
})
