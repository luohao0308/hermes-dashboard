import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskPanel from '@/components/TaskPanel.vue'

describe('TaskPanel', () => {
  it('renders task list', () => {
    const tasks = [
      { task_id: '1', name: '测试任务', status: 'running', progress: 50 }
    ]
    const wrapper = mount(TaskPanel, {
      props: { tasks }
    })
    expect(wrapper.find('.task-name').text()).toBe('测试任务')
  })

  it('displays progress correctly', () => {
    const tasks = [
      { task_id: '1', name: '测试任务', status: 'running', progress: 75 }
    ]
    const wrapper = mount(TaskPanel, {
      props: { tasks }
    })
    const progressText = wrapper.find('.progress-text').text()
    expect(progressText).toContain('75')
  })
})
