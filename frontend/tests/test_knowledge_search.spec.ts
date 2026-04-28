import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import KnowledgeSearch from '@/components/KnowledgeSearch.vue'

describe('KnowledgeSearch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        results: [
          {
            source: 'rca',
            item_id: 'report-1',
            session_id: 'session-12345678',
            run_id: 'run-12345678',
            title: 'Gateway timeout',
            summary: 'network: Gateway timeout',
            item_type: 'network',
            status: '0.8',
            created_at: '2026-04-29T08:00:00Z',
          },
        ],
      }),
    })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('searches and renders knowledge records', async () => {
    const wrapper = mount(KnowledgeSearch)
    await wrapper.find('input').setValue('gateway')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/agent/knowledge/search?q=gateway&limit=20'))
    expect(wrapper.text()).toContain('Gateway timeout')
    expect(wrapper.text()).toContain('network: Gateway timeout')
    expect(wrapper.text()).toContain('Session session-')
  })
})
