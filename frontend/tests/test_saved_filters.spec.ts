/**
 * Tests for useSavedFilters composable — OPT-51.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock localStorage
const storage: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => storage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { storage[key] = value }),
  removeItem: vi.fn((key: string) => { delete storage[key] }),
  clear: vi.fn(() => { for (const k in storage) delete storage[k] }),
  get length() { return Object.keys(storage).length },
  key: vi.fn((i: number) => Object.keys(storage)[i] ?? null),
}
vi.stubGlobal('localStorage', localStorageMock)

let useSavedFilters: typeof import('../src/composables/useSavedFilters')['useSavedFilters']

beforeEach(async () => {
  localStorageMock.clear()
  vi.clearAllMocks()
  const mod = await import('../src/composables/useSavedFilters')
  useSavedFilters = mod.useSavedFilters
})

describe('useSavedFilters', () => {
  it('returns defaults when no saved state', () => {
    const { filters, hasSaved } = useSavedFilters('test', { status: '', name: '' })
    expect(filters.value).toEqual({ status: '', name: '' })
    expect(hasSaved.value).toBe(false)
  })

  it('persists filters to localStorage on save', () => {
    const { filters, save } = useSavedFilters('runs', { status: '', runtime_id: '' })
    filters.value.status = 'running'
    save()
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'ai-control-plane:filters:runs',
      expect.stringContaining('"running"'),
    )
  })

  it('restores filters from localStorage', () => {
    storage['ai-control-plane:filters:audit'] = JSON.stringify({ action: 'create', actor_type: 'service' })
    const { filters, hasSaved } = useSavedFilters('audit', { action: '', actor_type: '' })
    expect(filters.value.action).toBe('create')
    expect(filters.value.actor_type).toBe('service')
    expect(hasSaved.value).toBe(true)
  })

  it('clears saved filters and resets to defaults', () => {
    storage['ai-control-plane:filters:runs'] = JSON.stringify({ status: 'error' })
    const { filters, clear, hasSaved } = useSavedFilters('runs', { status: '' })
    expect(filters.value.status).toBe('error')
    clear()
    expect(filters.value.status).toBe('')
    expect(hasSaved.value).toBe(false)
  })

  it('namespaces are isolated', () => {
    const runs = useSavedFilters('runs', { status: '' })
    const audit = useSavedFilters('audit', { action: '' })
    runs.filters.value.status = 'running'
    runs.save()
    expect(audit.filters.value.action).toBe('')
  })

  it('strips sensitive fields on save', () => {
    const { filters, save } = useSavedFilters('test', {
      status: '',
      token: '',
      api_key: '',
      password: '',
      name: '',
    })
    filters.value.status = 'active'
    filters.value.token = 'should-not-persist'
    filters.value.api_key = 'secret-key'
    filters.value.password = 'pass123'
    filters.value.name = 'test'
    save()
    const saved = JSON.parse(
      localStorageMock.setItem.mock.calls[0][1] as string,
    )
    expect(saved.status).toBe('active')
    expect(saved.name).toBe('test')
    expect(saved.token).toBeUndefined()
    expect(saved.api_key).toBeUndefined()
    expect(saved.password).toBeUndefined()
  })

  it('handles corrupted localStorage gracefully', () => {
    storage['ai-control-plane:filters:bad'] = '{invalid json'
    const { filters } = useSavedFilters('bad', { status: '' })
    expect(filters.value).toEqual({ status: '' })
  })

  it('merges saved values with defaults', () => {
    storage['ai-control-plane:filters:partial'] = JSON.stringify({ status: 'running' })
    const { filters } = useSavedFilters('partial', { status: '', runtime_id: 'default-rt' })
    expect(filters.value.status).toBe('running')
    expect(filters.value.runtime_id).toBe('default-rt')
  })
})
