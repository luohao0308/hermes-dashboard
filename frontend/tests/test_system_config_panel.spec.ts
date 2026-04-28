import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SystemConfigPanel from '@/components/SystemConfigPanel.vue'

describe('SystemConfigPanel', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      const body = url.includes('/api/model/info')
        ? { model: 'MiniMax-M2.7', provider: 'MiniMax' }
        : url.includes('/api/skills')
          ? { skills: [{ name: 'review', description: 'Code review' }] }
          : url.includes('/api/agent/tools')
            ? { tools: [{ name: 'get_status', description: 'Read status', risk: 'read' }] }
          : url.includes('/api/agent/guardrails')
            ? { tool_policies: [{ risk: 'read', decision: 'allow', description: 'Read-only' }] }
          : url.includes('/api/plugins')
            ? { plugins: [{ name: 'notion', description: 'Sync docs' }] }
            : url.includes('/api/cron/jobs')
              ? { jobs: [{ name: 'daily-check', schedule: '0 9 * * *' }] }
              : { profile: 'local', gateway: 'enabled' }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(body),
      })
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders model and resource counts', async () => {
    const wrapper = mount(SystemConfigPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('MiniMax-M2.7')
    expect(wrapper.text()).toContain('review')
    expect(wrapper.text()).toContain('get_status')
    expect(wrapper.text()).toContain('Read-only')
    expect(wrapper.text()).toContain('notion')
    expect(wrapper.text()).toContain('daily-check')
  })

  it('refreshes data when button is clicked', async () => {
    const wrapper = mount(SystemConfigPanel)
    await flushPromises()

    await wrapper.find('.refresh-btn').trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalled()
  })
})
