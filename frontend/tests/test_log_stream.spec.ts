import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LogStream from '@/components/LogStream.vue'

describe('LogStream', () => {
  it('renders empty state when no logs', () => {
    const wrapper = mount(LogStream, {
      props: { logs: [] }
    })
    expect(wrapper.find('.empty-state').text()).toBe('📜暂无日志')
  })

  it('renders log entries', () => {
    const logs = [
      { timestamp: '2024-01-01T10:00:00Z', message: '系统启动', type: 'info' as const }
    ]
    const wrapper = mount(LogStream, {
      props: { logs }
    })
    expect(wrapper.find('.log-message').text()).toBe('系统启动')
  })
})
