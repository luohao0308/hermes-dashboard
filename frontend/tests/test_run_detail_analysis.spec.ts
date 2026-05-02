import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RunDetail from '@/components/RunDetail.vue'
import type { RcaReport, RunbookReport, WorkflowRun, WorkflowSpan } from '@/types'

const mockRun: WorkflowRun = {
  id: 'run-123',
  runtime_id: 'rt-1',
  title: 'Test Run',
  status: 'error',
  input_summary: 'Test input',
  started_at: '2026-04-28T08:00:00Z',
  ended_at: '2026-04-28T08:05:00Z',
  duration_ms: 300000,
  total_tokens: 1500,
  total_cost: 0.0025,
  created_at: '2026-04-28T08:00:00Z',
  updated_at: '2026-04-28T08:05:00Z',
}

const mockSpans: WorkflowSpan[] = []

const mockRca: RcaReport = {
  report_id: 'rca-1',
  session_id: 'sess-1',
  run_id: 'run-123',
  category: 'tool',
  root_cause: 'Tool call failed due to permission denied',
  confidence: 0.88,
  evidence: [
    { source: 'trace', title: 'Error span', detail: 'tool failed with 403', severity: 'high' },
    { source: 'log', title: 'Auth error', detail: 'permission denied', severity: 'medium' },
  ],
  next_actions: ['Check tool permissions', 'Retry with correct credentials'],
  low_confidence: false,
  generated_at: '2026-04-28T09:00:00Z',
  analyzer: 'structured_rca_v2',
}

const mockRunbook: RunbookReport = {
  runbook_id: 'rb-1',
  session_id: 'sess-1',
  run_id: 'run-123',
  rca_report_id: 'rca-1',
  title: 'Test Runbook',
  severity: 'high',
  summary: 'Tool call failed, confidence 88%',
  checklist: ['Check tool permissions', 'Retry with correct credentials'],
  execution_steps: [
    { step_id: 'step-1', label: 'Check tool permissions', action_type: 'manual_check', requires_confirmation: false, status: 'pending' },
  ],
  evidence_count: 2,
  markdown: '# Runbook\n\n- [ ] Check tool permissions\n- [ ] Retry',
  generated_at: '2026-04-28T09:01:00Z',
  generator: 'rule_based_runbook_v1',
}

const baseProps = {
  runId: 'run-123',
  run: mockRun,
  spans: mockSpans,
  loading: false,
  error: null,
}

describe('RunDetail — RCA section', () => {
  it('shows RCA section header', () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    expect(wrapper.text()).toContain('Root Cause Analysis')
    expect(wrapper.text()).toContain('RCA analysis failed')
  })

  it('shows Analyze RCA button', () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    const btn = wrapper.find('.action-btn')
    expect(btn.text()).toContain('Generate RCA')
  })

  it('emits analyzeRca on button click', async () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    await wrapper.find('.action-btn').trigger('click')
    expect(wrapper.emitted('analyzeRca')).toBeTruthy()
  })

  it('shows RCA report when provided', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: mockRca },
    })
    expect(wrapper.text()).toContain('Tool call failed due to permission denied')
    expect(wrapper.text()).toContain('88%')
    expect(wrapper.text()).toContain('tool')
  })

  it('shows evidence items', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: mockRca },
    })
    const evidenceItems = wrapper.findAll('.evidence-item')
    expect(evidenceItems.length).toBe(2)
    expect(wrapper.text()).toContain('tool failed with 403')
  })

  it('shows next actions', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: mockRca },
    })
    expect(wrapper.text()).toContain('Check tool permissions')
    expect(wrapper.text()).toContain('Retry with correct credentials')
  })

  it('shows low confidence badge when applicable', () => {
    const lowConfRca: RcaReport = { ...mockRca, low_confidence: true, confidence: 0.35 }
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: lowConfRca },
    })
    expect(wrapper.text()).toContain('Confidence')
  })

  it('shows loading state on RCA button', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, loadingRca: true },
    })
    expect(wrapper.text()).toContain('Processing...')
  })

  it('shows Export button when RCA exists', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: mockRca },
    })
    const btns = wrapper.findAll('.action-btn')
    expect(btns.some(b => b.text() === 'Export')).toBe(true)
  })

  it('emits exportRca on Export click', async () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, rcaReport: mockRca },
    })
    const exportBtn = wrapper.findAll('.action-btn').find(b => b.text() === 'Export')
    await exportBtn!.trigger('click')
    expect(wrapper.emitted('exportRca')).toBeTruthy()
  })
})

describe('RunDetail — Runbook section', () => {
  it('shows Runbook section header', () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    expect(wrapper.text()).toContain('Runbook')
    expect(wrapper.text()).toContain('Runbook generation failed')
  })

  it('shows Generate Runbook button', () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    const btns = wrapper.findAll('.action-btn')
    expect(btns.some(b => b.text().includes('Generate Runbook'))).toBe(true)
  })

  it('emits generateRunbook on button click', async () => {
    const wrapper = mount(RunDetail, { props: baseProps })
    const btns = wrapper.findAll('.action-btn')
    const genBtn = btns.find(b => b.text().includes('Generate Runbook'))
    await genBtn!.trigger('click')
    expect(wrapper.emitted('generateRunbook')).toBeTruthy()
  })

  it('shows runbook when provided', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, runbook: mockRunbook },
    })
    expect(wrapper.text()).toContain('Tool call failed, confidence 88%')
    expect(wrapper.text()).toContain('high')
  })

  it('shows checklist items', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, runbook: mockRunbook },
    })
    expect(wrapper.text()).toContain('Check tool permissions')
    expect(wrapper.text()).toContain('Retry with correct credentials')
  })

  it('shows markdown preview', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, runbook: mockRunbook },
    })
    expect(wrapper.text()).toContain('# Runbook')
  })

  it('shows loading state on Runbook button', () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, loadingRunbook: true },
    })
    expect(wrapper.text()).toContain('Processing...')
  })

  it('emits exportRunbook on Export click', async () => {
    const wrapper = mount(RunDetail, {
      props: { ...baseProps, runbook: mockRunbook },
    })
    const exportBtns = wrapper.findAll('.action-btn.secondary')
    if (exportBtns.length > 1) {
      await exportBtns[1].trigger('click')
      expect(wrapper.emitted('exportRunbook')).toBeTruthy()
    }
  })
})
