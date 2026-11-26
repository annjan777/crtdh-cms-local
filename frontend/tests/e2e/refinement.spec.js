// Post-redesign refinement pass (26 Nov 2026): layout and behaviour that the parity tests do not cover.
import { expect, test } from '@playwright/test'
import { snapshot, visible } from './helpers.js'

const c = snapshot.collections

test('inner pages line up with the header logo at laptop width', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  for (const path of ['/about/', '/team/', '/services/', '/facilities/']) {
    await page.goto(path)
    const logo = await page.locator('.site-header__bar').evaluate((e) => e.getBoundingClientRect().left + parseFloat(getComputedStyle(e).paddingLeft))
    const content = await page.locator('main section .container').first().evaluate((e) => e.getBoundingClientRect().left + parseFloat(getComputedStyle(e).paddingLeft))
    expect(Math.abs(logo - content), path).toBeLessThan(2)
  }
})

test('about: the objectives are stages in order, each task once', async ({ page }) => {
  await page.goto('/about/')
  const stages = [...new Set(visible(c['objective-rows']).map((r) => r.category).filter(Boolean))]
  await expect(page.locator('.ab-process__stage')).toHaveCount(stages.length)
  const tasks = await page.locator('.ab-process__tasks li').allTextContents()
  expect(new Set(tasks).size).toBe(tasks.length)
  await expect(page.locator('table')).toHaveCount(0)
})

test('team: every portrait below the PI is the same size', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/team/')
  const widths = await page.locator('.tgrid .tp').evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().width)))
  expect(widths.length).toBeGreaterThan(1)
  expect(new Set(widths).size).toBe(1)
})

test('media: the catch-all album shows a selection, then every photo on request', async ({ page }) => {
  const album = visible(c['media-events']).find((e) => /ongoing activit|other activit/i.test(e.title))
  test.skip(!album || album.images.length <= 8, 'no large catch-all album in this snapshot')
  await page.goto('/media/')
  const section = page.locator('.news-acts')
  await expect(section.locator('.news-acts__btn')).toHaveCount(8)
  await section.getByRole('button', { name: `Show all ${album.images.length} photos` }).click()
  await expect(section.locator('.news-acts__btn')).toHaveCount(album.images.length)
  await section.locator('.news-acts__btn').nth(9).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  // It is not repeated in the event list.
  await expect(page.locator('.news-row__title', { hasText: album.title })).toHaveCount(0)
})

test('product: partner logos share one box size; partners without logos get no empty boxes', async ({ page }) => {
  await page.goto('/product/')
  const boxes = await page.locator('.pr__logo').evaluateAll((els) => els.map((e) => `${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`))
  expect(new Set(boxes).size).toBeLessThanOrEqual(1)
  for (const p of visible(c.products)) {
    if ((p.partners || []).length && !(p.partners || []).some((x) => x.logo)) {
      await expect(page.locator(`#product-${p.id} .pr__logo`)).toHaveCount(0)
    }
  }
})
