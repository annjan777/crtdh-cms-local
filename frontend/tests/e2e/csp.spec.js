// The built CSP (.htaccess, what CIC Apache sends) must not block anything the pages use (R-15 / F-12).
// The local static server sends no CSP, so each page is served here with the header from the build.
import fs from 'node:fs'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { ROUTES } from './helpers.js'

const htaccess = fs.readFileSync(path.resolve('build/client/.htaccess'), 'utf8')
const CSP = htaccess.match(/Content-Security-Policy "([^"]+)"/)[1]

test('the CSP blocks inline <style> elements but allows React style attributes', () => {
  expect(CSP).toContain("style-src-elem 'self'")
  expect(CSP).toContain("style-src-attr 'unsafe-inline'")
  expect(CSP).not.toMatch(/style-src-elem[^;]*unsafe-inline/)
})

for (const route of ROUTES) {
  test(`no CSP violation on ${route}`, async ({ page }) => {
    await page.route('**/*', async (r) => {
      if (r.request().resourceType() !== 'document') return r.continue()
      const res = await r.fetch()
      await r.fulfill({ response: res, headers: { ...res.headers(), 'content-security-policy': CSP } })
    })
    await page.addInitScript(() => {
      window.__csp = []
      document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`))
    })
    await page.goto(route, { waitUntil: 'networkidle' })
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y)
        await new Promise((r) => setTimeout(r, 40))
      }
    })
    await page.waitForTimeout(300)
    expect(await page.evaluate(() => window.__csp)).toEqual([])
  })
}

test('an injected inline <style> element is blocked', async ({ page }) => {
  await page.route('**/*', async (r) => {
    if (r.request().resourceType() !== 'document') return r.continue()
    const res = await r.fetch()
    const body = (await res.text()).replace('</head>', '<style>body{background:rgb(255,0,0)}</style></head>')
    await r.fulfill({ response: res, body, headers: { ...res.headers(), 'content-security-policy': CSP } })
  })
  await page.goto('/about/')
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).not.toBe('rgb(255, 0, 0)')
})
