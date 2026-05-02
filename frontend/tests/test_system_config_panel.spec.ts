import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SystemConfigPanel from '@/components/SystemConfigPanel.vue'

describe('SystemConfigPanel', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      const body = url.endsWith('/health')
        ? { service: 'ai-workflow-control-plane', version: '3.0.0', status: 'healthy', database: { status: 'connected', migration_version: '009' }, workers: { 'scheduler-worker': { status: 'alive', worker_id: 'worker-1' } } }
        : url.includes('/api/runtimes')
          ? { items: [{ name: 'MiniMax-M2.7', type: 'model', status: 'available' }] }
          : url.includes('/api/agent/tools')
            ? { tools: [{ name: 'get_status', description: 'Read status', risk: 'read' }] }
          : url.includes('/api/agent/guardrails')
            ? { tool_policies: [{ risk: 'read', decision: 'allow', description: 'Read-only' }] }
          : url.includes('/api/exports')
            ? { export_dir: '/tmp/hermes-exports', exists: true, files: [{ filename: 'session.md', path: '/tmp/hermes-exports/session.md', bytes: 42, updated_at: '2026-04-29T00:00:00Z' }], count: 1 }
          : url.includes('/api/agent/evals/summary')
            ? { total_runs: 5, success_rate: 0.8, avg_duration_seconds: 2.4, trend: [{ date: '2026-04-29', runs: 5, errors: 1, success_rate: 0.8, avg_duration_seconds: 2.4 }] }
          : url.includes('/api/metrics')
            ? { runs: { total: 5, running: 1 } }
            : {}

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
    expect(wrapper.text()).toContain('控制面配置')
    expect(wrapper.text()).toContain('get_status')
    expect(wrapper.text()).toContain('Read-only')
    expect(wrapper.text()).toContain('scheduler-worker')
    expect(wrapper.text()).toContain('/tmp/hermes-exports')
    expect(wrapper.text()).toContain('session.md')
    expect(wrapper.text()).toContain('Agent 性能趋势')
    expect(wrapper.text()).toContain('80.0%')
  })

  it('refreshes data when button is clicked', async () => {
    const wrapper = mount(SystemConfigPanel)
    await flushPromises()

    await wrapper.find('.refresh-btn').trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalled()
  })
})
