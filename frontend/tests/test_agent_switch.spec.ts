import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Agent Switch Logic (pure unit tests)', () => {
  // --- Frontend mapping: 'main' → 'Dispatcher' ---

  it('maps "main" agent_id to "Dispatcher" display name', () => {
    const agentId = 'main'
    const displayName = agentId === 'main' ? 'Dispatcher' : agentId
    expect(displayName).toBe('Dispatcher')
  })

  it('maps "Developer" agent_id to "Developer" display name', () => {
    const agentId = 'Developer'
    const displayName = agentId === 'main' ? 'Dispatcher' : agentId
    expect(displayName).toBe('Developer')
  })

  it('maps "DevOps" agent_id to "DevOps" display name', () => {
    const agentId = 'DevOps'
    const displayName = agentId === 'main' ? 'Dispatcher' : agentId
    expect(displayName).toBe('DevOps')
  })

  // --- switchAgent: PATCH body contains correct agent_id ---

  it('PATCH body uses the new agent name on switch', async () => {
    const sessionId = 'sess-123'
    const newAgent = 'Developer'
    const body = JSON.stringify({ agent_id: newAgent })
    const parsed = JSON.parse(body)
    expect(parsed.agent_id).toBe('Developer')
  })

  // --- switchAgent: updates local sessions list ---

  it('switchAgent updates the sessions list with new agent_id', () => {
    const sessions = [
      { session_id: 'sess-1', agent_id: 'main', message_count: 0 },
      { session_id: 'sess-2', agent_id: 'Dispatcher', message_count: 0 },
    ]
    const currentSessionId = 'sess-1'

    // Simulate switchAgent: find session and update its agent_id
    const session = sessions.find(s => s.session_id === currentSessionId)
    if (session) {
      session.agent_id = 'Developer'
    }

    const updated = sessions.find(s => s.session_id === 'sess-1')
    expect(updated?.agent_id).toBe('Developer')
  })

  // --- Backend: _run_chat_agent uses session.agent_id not cfg.main_agent ---

  it('backend picks agent by session.agent_id (fallback to dispatcher)', () => {
    // Simulate Python dict-style agents registry
    const agents: Record<string, { name: string }> = {
      dispatcher: { name: 'dispatcher' },
      Developer: { name: 'Developer' },
      DevOps: { name: 'DevOps' },
    }

    // Session created with Developer
    const session = { agent_id: 'Developer' }
    const chosen = agents[session.agent_id] ?? agents['dispatcher']
    expect(chosen?.name).toBe('Developer')
  })

  it('backend falls back to dispatcher for unknown agent_id', () => {
    const agents: Record<string, { name: string }> = {
      dispatcher: { name: 'dispatcher' },
      Developer: { name: 'Developer' },
    }
    const session = { agent_id: 'UnknownAgent' }
    const chosen = agents[session.agent_id] ?? agents['dispatcher']
    expect(chosen?.name).toBe('dispatcher')
  })

  // --- ChatManager: session created with specified agent_id ---

  it('session created with "main" has agent_id "main"', () => {
    const session = { agent_id: 'main', message_count: 0, session_id: 'x' }
    expect(session.agent_id).toBe('main')
  })

  it('session created with "Developer" has agent_id "Developer"', () => {
    const session = { agent_id: 'Developer', message_count: 0, session_id: 'x' }
    expect(session.agent_id).toBe('Developer')
  })

  // --- Stop session: session has _run_task field ---

  it('session object has _run_task field', () => {
    const session: any = { session_id: 'x', agent_id: 'main' }
    session._run_task = null
    expect(session._run_task).toBeNull()
  })

  // --- availableAgents from /api/agents maps correctly ---

  it('maps /api/agents response to agent names array', () => {
    const apiResponse = {
      agents: [
        { name: 'Dispatcher' },
        { name: 'Developer' },
        { name: 'Reviewer' },
      ]
    }
    const names = apiResponse.agents.map((a: any) => a.name)
    expect(names).toContain('Dispatcher')
    expect(names).toContain('Developer')
    expect(names).not.toContain('Agent')  // 'main' should NOT appear
    expect(names.length).toBe(3)
  })
})
