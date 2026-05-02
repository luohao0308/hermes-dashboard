import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ApprovalInbox from '@/components/ApprovalInbox.vue'
import type { ApprovalItem } from '@/types'

const mockApprovals: ApprovalItem[] = [
  {
    id: 'appr-1',
    run_id: 'run-aaa',
    status: 'pending',
    reason: 'Tool requires confirmation',
    requested_by: 'agent',
    created_at: '2026-04-28T08:00:00Z',
  },
  {
    id: 'appr-2',
    run_id: 'run-bbb',
    status: 'approved',
    reason: 'Safe read operation',
    requested_by: 'agent',
    resolved_by: 'admin',
    resolved_note: 'Approved for testing',
    created_at: '2026-04-28T07:00:00Z',
    resolved_at: '2026-04-28T07:05:00Z',
  },
  {
    id: 'appr-3',
    run_id: 'run-ccc',
    status: 'rejected',
    reason: 'Destructive operation',
    requested_by: 'agent',
    resolved_by: 'reviewer',
    resolved_note: 'Too risky',
    created_at: '2026-04-28T06:00:00Z',
    resolved_at: '2026-04-28T06:01:00Z',
  },
]

describe('ApprovalInbox', () => {
  it('renders approval items', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('Tool requires confirmation')
    expect(wrapper.text()).toContain('Safe read operation')
    expect(wrapper.text()).toContain('Destructive operation')
    expect(wrapper.text()).toContain('3 approval inbox')
  })

  it('shows approve/reject buttons for pending items', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    const approveBtns = wrapper.findAll('.approve-btn')
    const rejectBtns = wrapper.findAll('.reject-btn')
    expect(approveBtns.length).toBe(1)
    expect(rejectBtns.length).toBe(1)
  })

  it('shows resolution status for resolved items', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('Approved for testing')
    expect(wrapper.text()).toContain('Too risky')
  })

  it('shows empty state when no approvals', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('No pending approvals')
  })

  it('emits approve event', async () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    await wrapper.find('.approve-btn').trigger('click')
    expect(wrapper.emitted('approve')).toBeTruthy()
    expect(wrapper.emitted('approve')![0]).toEqual(['appr-1'])
  })

  it('emits reject event', async () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    await wrapper.find('.reject-btn').trigger('click')
    expect(wrapper.emitted('reject')).toBeTruthy()
    expect(wrapper.emitted('reject')![0]).toEqual(['appr-1'])
  })

  it('emits filterChange when status filter changes', async () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    await wrapper.find('.filter-select').setValue('pending')
    expect(wrapper.emitted('filterChange')).toBeTruthy()
    expect(wrapper.emitted('filterChange')![0]).toEqual(['pending'])
  })

  it('shows pagination when total exceeds limit', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals.slice(0, 2),
        total: 10,
        limit: 2,
        offset: 0,
      },
    })

    expect(wrapper.text()).toContain('1–2 / 10')
    expect(wrapper.find('.pagination').exists()).toBe(true)
  })

  it('emits pageChange on pagination click', async () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals.slice(0, 2),
        total: 10,
        limit: 2,
        offset: 0,
      },
    })

    const nextBtn = wrapper.findAll('.page-btn')[1]
    await nextBtn.trigger('click')
    expect(wrapper.emitted('pageChange')).toBeTruthy()
    expect(wrapper.emitted('pageChange')![0]).toEqual([2])
  })

  it('shows loading skeleton', () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: [],
        total: 0,
        limit: 50,
        offset: 0,
        loading: true,
      },
    })

    expect(wrapper.find('.state-loading').exists()).toBe(true)
  })

  it('emits refresh event', async () => {
    const wrapper = mount(ApprovalInbox, {
      props: {
        approvals: mockApprovals,
        total: 3,
        limit: 50,
        offset: 0,
      },
    })

    await wrapper.find('.refresh-btn').trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })
})
