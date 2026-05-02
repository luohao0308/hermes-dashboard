/**
 * Tests for AuditLogPanel — quick filters, request_id search, export.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AuditLogPanel from '../src/components/AuditLogPanel.vue'

// Stub child components
const stubs = {
  LoadingState: { template: '<div />' },
  EmptyState: { template: '<div />' },
}

const sampleLogs = [
  {
    id: '1',
    actor_type: 'user',
    actor_id: 'alice',
    action: 'created',
    resource_type: 'workflow',
    resource_id: 'wf-001',
    summary: 'user:alice created workflow wf-001',
    created_at: '2026-05-01T10:00:00Z',
  },
  {
    id: '2',
    actor_type: 'system',
    actor_id: null,
    action: 'updated',
    resource_type: 'run',
    resource_id: 'run-002',
    summary: 'system updated run run-00',
    created_at: '2026-05-01T11:00:00Z',
  },
]

function mountPanel(props = {}) {
  return mount(AuditLogPanel, {
    props: {
      logs: sampleLogs,
      total: 2,
      limit: 50,
      offset: 0,
      loading: false,
      ...props,
    },
    stubs,
  })
}

describe('AuditLogPanel', () => {
  it('renders log entries', () => {
    const wrapper = mountPanel()
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('alice')
    expect(rows[0].text()).toContain('created')
  })

  it('renders resource_id filter input', () => {
    const wrapper = mountPanel()
    const inputs = wrapper.findAll('.filter-input')
    expect(inputs).toHaveLength(2)
    expect(inputs[1].attributes('placeholder')).toContain('Request')
  })

  it('emits filterChange with resource_id', async () => {
    const wrapper = mountPanel()
    const input = wrapper.findAll('.filter-input')[1]
    await input.setValue('req-123')
    await input.trigger('change')
    expect(wrapper.emitted('filterChange')).toBeTruthy()
    const last = wrapper.emitted('filterChange')!.at(-1)![0]
    expect(last).toHaveProperty('resource_id', 'req-123')
  })

  it('shows quick filter chips when filters active', async () => {
    const wrapper = mountPanel()
    expect(wrapper.find('.quick-filters').exists()).toBe(false)
    const selects = wrapper.findAll('.filter-select')
    await selects[0].setValue('user')
    await selects[0].trigger('change')
    expect(wrapper.find('.quick-filters').exists()).toBe(true)
    expect(wrapper.find('.filter-chip').text()).toContain('user')
  })

  it('clears individual filter on chip click', async () => {
    const wrapper = mountPanel()
    const selects = wrapper.findAll('.filter-select')
    await selects[0].setValue('user')
    await selects[0].trigger('change')
    await selects[2].setValue('created')
    await selects[2].trigger('change')
    const chips = wrapper.findAll('.filter-chip')
    expect(chips).toHaveLength(2)
    await chips[0].trigger('click')
    const last = wrapper.emitted('filterChange')!.at(-1)![0]
    expect(last.actor_type).toBe('')
    expect(last.action).toBe('created')
  })

  it('clears all filters', async () => {
    const wrapper = mountPanel()
    const selects = wrapper.findAll('.filter-select')
    await selects[0].setValue('user')
    await selects[0].trigger('change')
    await selects[2].setValue('created')
    await selects[2].trigger('change')
    await wrapper.find('.chip-clear-all').trigger('click')
    const last = wrapper.emitted('filterChange')!.at(-1)![0]
    expect(last).toEqual({ actor_type: '', actor_id: '', action: '', resource_type: '', resource_id: '' })
  })

  it('emits pageChange on pagination click', async () => {
    const wrapper = mountPanel({ total: 100, offset: 0 })
    await wrapper.findAll('.page-btn')[1].trigger('click')
    expect(wrapper.emitted('pageChange')).toEqual([[50]])
  })

  it('disables export buttons when no logs', () => {
    const wrapper = mountPanel({ logs: [], total: 0 })
    const exportBtns = wrapper.findAll('.export-group .btn')
    expect(exportBtns[0].attributes('disabled')).toBeDefined()
    expect(exportBtns[1].attributes('disabled')).toBeDefined()
  })

  it('export buttons enabled when logs present', () => {
    const wrapper = mountPanel()
    const exportBtns = wrapper.findAll('.export-group .btn')
    expect(exportBtns[0].attributes('disabled')).toBeUndefined()
    expect(exportBtns[1].attributes('disabled')).toBeUndefined()
  })
})
