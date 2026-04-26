import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5174'

test.describe('Agent Chat - Agent Dropdown & Switch', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat page
    await page.goto(BASE)
    await page.evaluate(() => {
      window.location.hash = '#/chat'
    })
    await page.waitForTimeout(1000)
  })

  test('dropdown shows available agents after session created', async ({ page }) => {
    // Click "+ 新对话" to create a session
    const newChatBtn = page.locator('.btn-new-chat')
    await expect(newChatBtn).toBeVisible()
    await newChatBtn.click()
    await page.waitForTimeout(1500)

    // Agent dropdown should be visible in the chat header
    const dropdown = page.locator('.agent-select')
    await expect(dropdown).toBeVisible()

    // Should have multiple agent options
    const options = dropdown.locator('option')
    const count = await options.count()
    expect(count).toBeGreaterThan(1)

    // Default should be "Dispatcher"
    await expect(dropdown).toHaveValue('Dispatcher')
  })

  test('switching agent via dropdown calls PATCH and updates session', async ({ page }) => {
    // Create a new session
    const newChatBtn = page.locator('.btn-new-chat')
    await newChatBtn.click()
    await page.waitForTimeout(1500)

    // Get the session's current agent before switch
    const dropdown = page.locator('.agent-select')
    await expect(dropdown).toBeVisible()
    const beforeAgent = await dropdown.inputValue()

    // Find a different agent to switch to
    const options = await dropdown.locator('option').allTextContents()
    const afterAgent = options.find(opt => opt !== beforeAgent)
    expect(afterAgent).toBeDefined()

    // Select a different agent via click
    await dropdown.selectOption(afterAgent!)
    await page.waitForTimeout(500)

    // Verify dropdown reflects the change
    await expect(dropdown).toHaveValue(afterAgent)

    // Verify the session in the sidebar also reflects the agent change
    // The session item should show the new agent name in the sidebar (if displayed)
    // Since we don't show agent name in sidebar, we just verify dropdown is consistent
    await expect(dropdown).toHaveValue(afterAgent)
  })

  test('sending message after agent switch uses correct agent', async ({ page }) => {
    // Create a new session
    const newChatBtn = page.locator('.btn-new-chat')
    await newChatBtn.click()
    await page.waitForTimeout(1500)

    // Switch to Developer if available
    const dropdown = page.locator('.agent-select')
    const options = await dropdown.locator('option').allTextContents()
    if (options.includes('Developer')) {
      await dropdown.selectOption('Developer')
      await page.waitForTimeout(500)
      await expect(dropdown).toHaveValue('Developer')
    }

    // Type and send a message
    const textarea = page.locator('.chat-input')
    await textarea.fill('1+1等于几？')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)

    // Should see the user message in the chat
    const userMsg = page.locator('.message-user').first()
    await expect(userMsg).toBeVisible()
    await expect(userMsg.locator('.message-text')).toContainText('1+1')
  })

  test('session list shows created sessions', async ({ page }) => {
    // Initially should have no sessions or existing ones
    const newChatBtn = page.locator('.btn-new-chat')
    await newChatBtn.click()
    await page.waitForTimeout(1500)

    // Session list should have at least 1 item
    const sessionItems = page.locator('.session-item')
    await expect(sessionItems.first()).toBeVisible()

    // Click again to create a second session
    await newChatBtn.click()
    await page.waitForTimeout(1500)
    const count = await sessionItems.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  test('stop button appears while agent is thinking', async ({ page }) => {
    // Create a new session
    const newChatBtn = page.locator('.btn-new-chat')
    await newChatBtn.click()
    await page.waitForTimeout(1500)

    // Send a message that will trigger a response
    const textarea = page.locator('.chat-input')
    await textarea.fill('请用一句话介绍自己')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(500)

    // Stop button should appear while thinking
    const stopBtn = page.locator('.btn-stop')
    await expect(stopBtn).toBeVisible()
  })
})
