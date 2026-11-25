import { expect, test } from '@playwright/test'

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })

test('phone menu lists Contact us once (the header button), not again in the list', async ({ page }) => {
  await page.goto('/about/')
  await page.click('.nav-toggle')
  await expect(page.locator('#mobile-nav')).toBeVisible()
  await expect(page.locator('#mobile-nav a', { hasText: 'Contact us' })).toHaveCount(0)
  await expect(page.locator('.site-header__cta', { hasText: 'Contact us' })).toBeVisible()
})

test('a page opened from the phone menu starts at the top, not where the last page was', async ({ page }) => {
  await page.goto('/about/')
  await page.evaluate(() => window.scrollTo({ top: 1500, behavior: 'instant' }))
  await page.click('.nav-toggle')
  await page.locator('#mobile-nav a', { hasText: 'Services' }).click()
  await expect(page).toHaveURL(/\/services\/$/)
  await page.waitForTimeout(800)
  expect(await page.evaluate(() => window.scrollY)).toBe(0)
})

test('back-to-top button appears after scrolling and returns to the top', async ({ page }) => {
  await page.goto('/services/')
  const button = page.getByRole('button', { name: 'Back to top' })
  await expect(page.locator('.back-to-top.is-shown')).toHaveCount(0)
  await page.evaluate(() => window.scrollTo({ top: 2500, behavior: 'instant' }))
  await expect(button).toBeVisible()
  await button.click()
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0)
})
