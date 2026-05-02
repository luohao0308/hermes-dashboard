import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AlertsPanel from '@/components/AlertsPanel.vue'

describe('AlertsPanel', () => {
  it('renders critical alerts and emits action', async () => {
    const alert = {
      id: 'a1',
      severity: 'critical' as const,
      title: 'Gateway 未运行',
      message: 'Hermès Gateway 当前未运行',
      source: 'status',
      session_id: 'session-1',
      action_label: '查看日志',
      action_nav: 'logs',
      created_at: '2026-04-28T08:00:00Z',
    }
    const wrapper = mount(AlertsPanel, {
      props: {
        alerts: [alert],
      },
    })

    expect(wrapper.text()).toContain('Gateway 未运行')
    expect(wrapper.text()).toContain('Critical')

    await wrapper.findAll('.action-btn')[1].trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual([alert])

    await wrapper.findAll('.action-btn')[0].trigger('click')
    expect(wrapper.emitted('runbook')?.[0]).toEqual([alert])
  })

  it('emits refresh', async () => {
    const wrapper = mount(AlertsPanel, {
      props: {
        alerts: [],
      },
    })

    await wrapper.find('.refresh-btn').trigger('click')

    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })
})
