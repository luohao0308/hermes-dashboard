import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import zhCN from '../src/i18n/zh-CN'
import enUS from '../src/i18n/en-US'
import { setLocale, getLocale } from '../src/i18n'
import Sidebar from '../src/components/Sidebar.vue'
import TopBar from '../src/components/TopBar.vue'

describe('i18n', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('switches locale between zh-CN and en-US', () => {
    setLocale('zh-CN')
    expect(getLocale()).toBe('zh-CN')

    setLocale('en-US')
    expect(getLocale()).toBe('en-US')
  })

  it('persists locale to localStorage', () => {
    setLocale('zh-CN')
    expect(localStorage.getItem('hermes_locale')).toBe('zh-CN')

    setLocale('en-US')
    expect(localStorage.getItem('hermes_locale')).toBe('en-US')
  })

  it('Sidebar renders zh-CN labels', () => {
    setLocale('zh-CN')
    const wrapper = mount(Sidebar, {
      props: { activeView: 'dashboard', isConnected: true },
    })

    expect(wrapper.text()).toContain('AI Control Plane')
    expect(wrapper.text()).toContain('仪表盘')
    expect(wrapper.text()).toContain('运行记录')
    expect(wrapper.text()).toContain('工作流')
    expect(wrapper.text()).toContain('已连接')
  })

  it('Sidebar renders en-US labels', () => {
    setLocale('en-US')
    const wrapper = mount(Sidebar, {
      props: { activeView: 'dashboard', isConnected: true },
    })

    expect(wrapper.text()).toContain('AI Control Plane')
    expect(wrapper.text()).toContain('Dashboard')
    expect(wrapper.text()).toContain('Runs')
    expect(wrapper.text()).toContain('Workflows')
    expect(wrapper.text()).toContain('Connected')
  })

  it('TopBar renders zh-CN labels', () => {
    setLocale('zh-CN')
    const wrapper = mount(TopBar, {
      props: {
        title: '仪表盘',
        hermesStatus: { gateway_running: true },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('网关运行中')
    expect(wrapper.text()).toContain('刷新')
  })

  it('TopBar renders en-US labels', () => {
    setLocale('en-US')
    const wrapper = mount(TopBar, {
      props: {
        title: 'Dashboard',
        hermesStatus: { gateway_running: false },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('Gateway stopped')
    expect(wrapper.text()).toContain('Refresh')
  })

  it('zh-CN and en-US have matching key structure', () => {
    function getKeys(obj: Record<string, any>, prefix = ''): string[] {
      return Object.entries(obj).flatMap(([key, val]) => {
        const fullKey = prefix ? `${prefix}.${key}` : key
        if (typeof val === 'object' && val !== null) {
          return getKeys(val, fullKey)
        }
        return [fullKey]
      })
    }

    const zhKeys = getKeys(zhCN as Record<string, any>).sort()
    const enKeys = getKeys(enUS as Record<string, any>).sort()

    const missingInEn = zhKeys.filter(k => !enKeys.includes(k))
    const missingInZh = enKeys.filter(k => !zhKeys.includes(k))

    expect(missingInEn).toEqual([])
    expect(missingInZh).toEqual([])
  })
})
