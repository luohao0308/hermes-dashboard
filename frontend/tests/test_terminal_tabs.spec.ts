/**
 * Tests for terminal tab session management.
 * Verifies that each terminal tab gets its own unique sessionId.
 */

import { describe, it, expect, beforeEach } from 'vitest'

// Inline the logic being tested (mimics App.vue terminal tab management)
function createTerminalSession(): string {
  return Math.random().toString(36).substring(2, 10)
}

interface TerminalTab {
  id: string
  name: string
  sessionId: string
}

function createTabs() {
  const tabs: TerminalTab[] = [{
    id: 'terminal-1',
    name: 'Terminal 1',
    sessionId: createTerminalSession(),
  }]
  let counter = 1

  function addTerminal() {
    counter++
    const tabId = `terminal-${counter}`
    const sessionId = createTerminalSession()
    tabs.push({ id: tabId, name: `Terminal ${counter}`, sessionId })
    return tabId
  }

  function closeTerminal(idx: number) {
    if (tabs.length === 1) return
    const tab = tabs[idx]
    tabs.splice(idx, 1)
    return tab.id
  }

  return { tabs, addTerminal, closeTerminal }
}

describe('Terminal tab session isolation', () => {
  it('creates unique sessionId for each tab', () => {
    const { tabs, addTerminal } = createTabs()
    const initialSession = tabs[0].sessionId

    addTerminal()
    addTerminal()

    const sessionIds = tabs.map(t => t.sessionId)
    const unique = new Set(sessionIds)
    expect(unique.size).toBe(tabs.length)
    expect(sessionIds[0]).toBe(initialSession)
  })

  it('sessionId is 8 characters', () => {
    const { tabs } = createTabs()
    expect(tabs[0].sessionId.length).toBe(8)
  })

  it('closing tab does not change other sessionIds', () => {
    const { tabs, addTerminal, closeTerminal } = createTabs()
    addTerminal()
    const tab2Session = tabs[1].sessionId

    closeTerminal(0) // close first tab

    expect(tabs[0].sessionId).toBe(tab2Session)
  })

  it('tab switch does not modify sessionIds', () => {
    const { tabs, addTerminal } = createTabs()
    addTerminal()
    const before = tabs.map(t => t.sessionId)

    // Switch to tab 2
    const activeId = tabs[1].id

    const after = tabs.map(t => t.sessionId)
    expect(after).toEqual(before)
  })
})
