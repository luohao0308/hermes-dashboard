import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EvalDashboard from '@/components/EvalDashboard.vue'
import ConfigCompare from '@/components/ConfigCompare.vue'
import type {
  EvalSummaryData,
  ConfigVersionItem,
  ConfigCompareData,
} from '@/types'

const emptySummary: EvalSummaryData = {
  total: 0,
  passed: 0,
  failed: 0,
  avg_score: null,
  avg_latency_ms: null,
  avg_cost: null,
  tool_error_rate: null,
  handoff_count: null,
  approval_count: null,
  by_runtime: [],
  by_config_version: [],
  trend: [],
}

const sampleSummary: EvalSummaryData = {
  total: 10,
  passed: 8,
  failed: 2,
  avg_score: 0.82,
  avg_latency_ms: 150.5,
  avg_cost: 0.0032,
  tool_error_rate: 0.05,
  handoff_count: 3,
  approval_count: 1,
  by_runtime: [
    { runtime_id: 'rt-1', runtime_name: 'CI Pipeline', total: 6, passed: 5, failed: 1, avg_score: 0.85 },
    { runtime_id: 'rt-2', runtime_name: 'Code Review', total: 4, passed: 3, failed: 1, avg_score: 0.78 },
  ],
  by_config_version: [
    { config_version: 'v1', total: 10, passed: 8, failed: 2, avg_score: 0.82 },
  ],
  trend: [
    { date: '2026-04-28', runs: 5, passed: 4, failed: 1, avg_score: 0.8, avg_latency_ms: 120, avg_cost: 0.003, tool_error_rate: 0.05, handoff_count: 1, approval_count: 0 },
    { date: '2026-04-29', runs: 5, passed: 4, failed: 1, avg_score: 0.84, avg_latency_ms: 180, avg_cost: 0.0034, tool_error_rate: 0.04, handoff_count: 2, approval_count: 1 },
  ],
}

describe('EvalDashboard', () => {
  it('renders empty state when no data', () => {
    const wrapper = mount(EvalDashboard, {
      props: { summary: emptySummary, loading: false },
    })
    expect(wrapper.text()).toContain('No eval data')
  })

  it('renders summary cards with data', () => {
    const wrapper = mount(EvalDashboard, {
      props: { summary: sampleSummary, loading: false },
    })
    expect(wrapper.text()).toContain('Total')
    expect(wrapper.text()).toContain('10')
    expect(wrapper.text()).toContain('Pass Rate')
    expect(wrapper.text()).toContain('80.0%')
  })

  it('renders runtime breakdown table', () => {
    const wrapper = mount(EvalDashboard, {
      props: { summary: sampleSummary, loading: false },
    })
    expect(wrapper.text()).toContain('By Runtime')
    expect(wrapper.text()).toContain('CI Pipeline')
    expect(wrapper.text()).toContain('Code Review')
  })

  it('renders trend section', () => {
    const wrapper = mount(EvalDashboard, {
      props: { summary: sampleSummary, loading: false },
    })
    expect(wrapper.text()).toContain('Daily Trend')
    expect(wrapper.text()).toContain('4/28')
    expect(wrapper.text()).toContain('4/29')
  })

  it('emits refresh when refresh button clicked', async () => {
    const wrapper = mount(EvalDashboard, {
      props: { summary: emptySummary, loading: false },
    })
    await wrapper.find('.refresh-btn').trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })
})

const mockVersions: ConfigVersionItem[] = [
  { id: 'cv-1', runtime_id: 'rt-1', config_type: 'workflow', version: 'v1', config_json: { model: 'gpt-4' }, evaluation_score: 0.8, requires_approval: false, created_by: 'alice', created_at: '2026-04-28T00:00:00Z' },
  { id: 'cv-2', runtime_id: 'rt-1', config_type: 'workflow', version: 'v2', config_json: { model: 'claude-3' }, evaluation_score: 0.9, requires_approval: true, created_by: 'bob', created_at: '2026-04-29T00:00:00Z' },
]

const mockCompareResult: ConfigCompareData = {
  before: mockVersions[0],
  after: mockVersions[1],
  score_delta: 0.1,
  changes: [
    { field: 'model', before: 'gpt-4', after: 'claude-3' },
  ],
  requires_approval: true,
}

describe('ConfigCompare', () => {
  it('renders empty state before comparison', () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: null, loading: false },
    })
    expect(wrapper.text()).toContain('Select two config versions')
  })

  it('renders comparison result', () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: mockCompareResult, loading: false },
    })
    expect(wrapper.text()).toContain('Score Delta')
    expect(wrapper.text()).toContain('+0.1')
    expect(wrapper.text()).toContain('Requires Approval')
    expect(wrapper.text()).toContain('model')
    expect(wrapper.text()).toContain('gpt-4')
    expect(wrapper.text()).toContain('claude-3')
  })

  it('renders changes count', () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: mockCompareResult, loading: false },
    })
    expect(wrapper.text()).toContain('Changes (1)')
  })

  it('emits compare event with selected versions', async () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: null, loading: false },
    })

    const selects = wrapper.findAll('select')
    await selects[0].setValue('cv-1')
    await selects[1].setValue('cv-2')
    await wrapper.find('.compare-btn').trigger('click')

    expect(wrapper.emitted('compare')).toBeTruthy()
    expect(wrapper.emitted('compare')![0]).toEqual(['cv-1', 'cv-2'])
  })

  it('disables compare button when same version selected', async () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: null, loading: false },
    })

    const selects = wrapper.findAll('select')
    await selects[0].setValue('cv-1')
    await selects[1].setValue('cv-1')

    const btn = wrapper.find('.compare-btn')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('renders version detail cards', () => {
    const wrapper = mount(ConfigCompare, {
      props: { versions: mockVersions, result: mockCompareResult, loading: false },
    })
    expect(wrapper.text()).toContain('Before: v1')
    expect(wrapper.text()).toContain('After: v2')
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('bob')
  })
})
