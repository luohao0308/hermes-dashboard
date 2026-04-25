import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HistoryList from '@/components/HistoryList.vue'

describe('HistoryList', () => {
  it('renders empty state when no history', () => {
    const wrapper = mount(HistoryList, {
      props: { history: [] }
    })
    expect(wrapper.find('.empty-state').text()).toBe('暂无历史任务')
  })

  it('renders history entries', () => {
    const history = [
      { task_id: '1', name: '已完成任务', completed_at: '2024-01-01T12:00:00Z', duration: 120 }
    ]
    const wrapper = mount(HistoryList, {
      props: { history }
    })
    expect(wrapper.find('.history-name').text()).toBe('已完成任务')
  })
})
