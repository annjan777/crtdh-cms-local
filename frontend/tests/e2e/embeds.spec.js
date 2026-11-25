// R-8 / F-06: no request leaves for Google or YouTube until the visitor asks for the map or a video.
import { expect, test } from '@playwright/test'
import { ROUTES } from './helpers.js'

const THIRD_PARTY = /(^|\.)(google\.com|gstatic\.com|youtube\.com|youtube-nocookie\.com|ytimg\.com|googlevideo\.com)$/

function watch(page) {
  const hits = []
  page.on('request', (r) => {
    const host = new URL(r.url()).hostname
    if (THIRD_PARTY.test(host)) hits.push(r.url())
  })
  return hits
}

for (const route of ROUTES) {
  test(`no Google or YouTube request on page load: ${route}`, async ({ page }) => {
    const hits = watch(page)
    await page.goto(route, { waitUntil: 'networkidle' })
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y)
        await new Promise((r) => setTimeout(r, 40))
      }
    })
    await page.waitForTimeout(300)
    expect(hits).toEqual([])
    await expect(page.locator('iframe[src*="google.com"], iframe[src*="youtube"]')).toHaveCount(0)
  })
}

test('the map loads only after "Show the map"', async ({ page }) => {
  await page.route(/google\.com/, (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>map</p>' }))
  await page.goto('/contact/')
  const show = page.getByRole('button', { name: 'Show the map' })
  test.skip(!(await show.count()), 'no map URL in this snapshot')
  await expect(page.getByRole('link', { name: 'Directions in Google Maps' })).toHaveAttribute('href', /google\.com\/maps\/search/)
  const box = await page.locator('.contact-map').boundingBox()
  await show.click()
  await expect(page.locator('.contact-map iframe[src^="https://www.google.com/maps/embed"]')).toHaveCount(1)
  expect((await page.locator('.contact-map').boundingBox()).height).toBe(box.height) // no layout jump
})

test('a video loads only after "Watch"', async ({ page }) => {
  await page.route(/youtube-nocookie\.com/, (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<p>player</p>' }))
  let found = null
  for (const route of ['/', '/covid-19/', '/social-impact/', '/enterprises/', '/innovations/']) {
    await page.goto(route)
    if (await page.locator('button[data-youtube]').count()) {
      found = route
      break
    }
  }
  test.skip(!found, 'no YouTube video in this snapshot')
  const poster = page.locator('button[data-youtube]').first()
  await expect(poster).toHaveAccessibleName(/^Watch/)
  await poster.click()
  await expect(page.locator('iframe[src^="https://www.youtube-nocookie.com/embed/"]').first()).toBeVisible()
})
