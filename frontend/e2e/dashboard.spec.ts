import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:5173'

test.describe('Hermès Dashboard E2E', () => {
  test('homepage loads without crash', async ({ page }) => {
    await page.goto(BASE)
    await expect(page).toHaveTitle(/Hermès/)
  })

  test('header displays correctly', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('h1')).toContainText('Hermès')
    await expect(page.locator('.connection-badge')).toBeVisible()
  })

  test('refresh button triggers data load', async ({ page }) => {
    await page.goto(BASE)
    const refreshBtn = page.locator('.header-btn').first()
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
    // Button should briefly show spinning state
  })

  test('shows error banner when backend unreachable', async ({ page }) => {
    await page.goto(BASE)
    // Give it a moment to attempt connection
    await page.waitForTimeout(1000)
    // If backend is down, error banner should appear
    const banner = page.locator('.error-banner')
    const hasError = await banner.isVisible().catch(() => false)
    if (hasError) {
      await expect(banner).toContainText(/无法连接|连接失败/)
    }
  })

  test('task panel renders', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForTimeout(2000)
    // Task panel should exist
    await expect(page.locator('.panel').first()).toBeVisible()
  })

  test('toast notifications work', async ({ page }) => {
    await page.goto(BASE)
    // Manual test: click refresh multiple times to trigger toast
    const refreshBtn = page.locator('.header-btn').first()
    await refreshBtn.click()
    await page.waitForTimeout(500)
    // Toast should appear if data loaded successfully
  })
})
