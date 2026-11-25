import { mediaRoot } from '../../scripts/media-root.mjs'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { ROUTES, isAllowedRequest } from './helpers.js'

for (const route of ROUTES) {
  test.describe(`page ${route}`, () => {
    test('prerendered HTML holds the content and the build marker before any script runs', async ({ request }) => {
      const res = await request.get(route)
      expect(res.status()).toBe(200)
      const html = await res.text()
      // The h1 may wrap its lines in spans (home hero); what matters is text in the HTML.
      expect(html).toMatch(/<h1[^>]*>(?:<span[^>]*>)*[^<]+/)
      expect(html).toMatch(/<meta name="crtdh-build" content="[^"]+"/)
      expect(html).toMatch(/<meta name="crtdh-snapshot" content="[^"]+"/)
      expect(html).toMatch(/<link rel="canonical" href="https:\/\/[^"]+"/)
      expect(html).toMatch(/<meta name="description" content="[^"]{40,}"/)
      expect(html).toMatch(/<meta property="og:image" content="https?:\/\/[^"]+"/)
      expect(html).not.toMatch(/localhost:8000|\/api\/v1\//)
    })

    test('makes no API requests (only its own static files)', async ({ page, baseURL }) => {
      const bad = []
      page.on('request', (r) => {
        if (!isAllowedRequest(r.url(), baseURL)) bad.push(r.url())
      })
      await page.goto(route, { waitUntil: 'networkidle' })
      await page.mouse.wheel(0, 20000)
      await page.waitForTimeout(300)
      expect(bad).toEqual([])
    })

    for (const width of [375, 768, 1280]) {
      test(`no horizontal overflow at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 900 })
        await page.goto(route, { waitUntil: 'networkidle' })
        const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
        expect(over).toBeLessThanOrEqual(0)
      })
    }

    for (const width of [375, 1280]) {
      test(`axe: no serious or critical violations at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 900 })
        await page.goto(route, { waitUntil: 'networkidle' })
        const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).exclude('iframe').analyze()
        const serious = results.violations
          .filter((v) => ['serious', 'critical'].includes(v.impact))
          .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`)
        expect(serious).toEqual([])
      })
    }

    test('landmarks, skip link and one h1', async ({ page }) => {
      await page.goto(route)
      await expect(page.locator('header.site-header')).toHaveCount(1)
      await expect(page.locator('main#main-content')).toHaveCount(1)
      await expect(page.locator('footer.site-footer')).toHaveCount(1)
      await expect(page.locator('h1')).toHaveCount(1)
      await page.keyboard.press('Tab')
      await expect(page.locator('.skip-link')).toBeFocused()
    })
  })
}

test('font families are limited to the approved set', async ({ page }) => {
  const used = new Set()
  for (const route of ROUTES) {
    await page.goto(route)
    const fams = await page.evaluate(() => [...document.querySelectorAll('body *:not(source):not(track):not(script):not(style)')].map((el) => getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim()))
    fams.forEach((f) => used.add(f))
  }
  // The previous design's faces, plus the v4 redesign's Alegreya and Atkinson Hyperlegible Next; all self-hosted. 'Caveat' is the Team page quote's decorative face (falls back to cursive).
  expect([...used].filter((f) => !['Open Sans', 'Montserrat', 'Caveat', 'Alegreya', 'Atkinson Hyperlegible Next'].includes(f))).toEqual([])
})

test('unknown paths get the 404 page (status 404) and it hydrates without errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  const res = await page.goto('/no/such/page', { waitUntil: 'networkidle' })
  expect(res.status()).toBe(404)
  await expect(page.locator('h1')).toHaveText('Page not found')
  await page.getByRole('link', { name: 'Back to home' }).click()
  await expect(page).toHaveURL(/\/$/)
  expect(errors).toEqual([])
})

test('sitemap and robots list every public route', async ({ request }) => {
  const xml = await (await request.get('/sitemap.xml')).text()
  for (const r of ROUTES) expect(xml).toContain(`${r === '/' ? '/' : r}</loc>`)
  expect(await (await request.get('/robots.txt')).text()).toContain('Sitemap:')
})

test('home carries Organization JSON-LD', async ({ request }) => {
  const html = await (await request.get('/')).text()
  const ld = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => JSON.parse(m[1]))
  expect(ld.some((x) => x['@type'] === 'ResearchOrganization' && x.name.includes('CRTDH'))).toBe(true)
})

test('placeholder sweep passes on the build', () => {
  const out = execFileSync('node', ['scripts/sweep.mjs'], { encoding: 'utf8', env: { ...process.env, MEDIA_ROOT: mediaRoot() } })
  expect(out).toContain('clean')
})

test('client-side navigation loads static .data files only', async ({ page, baseURL }) => {
  const bad = []
  page.on('request', (r) => {
    if (!isAllowedRequest(r.url(), baseURL)) bad.push(r.url())
  })
  await page.goto('/')
  await page.locator('footer').getByRole('link', { name: 'Team' }).click()
  await expect(page.locator('h1')).toHaveText('PI, Co-PIs and Research Team')
  await page.locator('footer').getByRole('link', { name: 'Innovations' }).click()
  await expect(page.locator('h1')).toHaveText('Devices & diagnostics from the lab bench to the clinic')
  expect(bad).toEqual([])
})

test('every sitemap URL ends with "/" and is the canonical and og:url of the page it serves', async ({ request }) => {
  const xml = await (await request.get('/sitemap.xml')).text()
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
  expect(locs).toHaveLength(ROUTES.length)
  for (const loc of locs) {
    expect(loc.endsWith('/')).toBe(true)
    const path = new URL(loc).pathname
    const res = await request.get(path, { maxRedirects: 0 })
    expect(res.status()).toBe(200)
    const html = await res.text()
    expect(html).toContain(`<link rel="canonical" href="${loc}"/>`)
    expect(html).toContain(`<meta property="og:url" content="${loc}"/>`)
  }
})

test('internal page links all end with "/"', async ({ request }) => {
  for (const r of ROUTES) {
    const html = await (await request.get(r)).text()
    const body = html.slice(html.indexOf('<body'))
    for (const m of body.matchAll(/<a\b[^>]*\shref="(\/[^"]*)"/g)) {
      const path = m[1].split(/[?#]/)[0]
      if (/\.\w{2,5}$/.test(path)) continue // files (/_media/x.pdf)
      expect(path, `${r} links to ${m[1]}`).toMatch(/\/$/)
    }
  }
})

test('.htaccess needs only AllowOverride FileInfo and guards every module block', async () => {
  const ht = fs.readFileSync(path.resolve('build/client/.htaccess'), 'utf8')
  const code = ht.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#'))
  for (const banned of [/^\s*Options\b/, /^\s*Expires/, /^\s*DirectorySlash\b/, /^\s*(Auth|Require|Order|Allow|Deny)\b/]) {
    expect(code.filter((l) => banned.test(l))).toEqual([])
  }
  // Header / SetEnvIf / AddType only inside the matching <IfModule>.
  const stack = []
  for (const l of code) {
    const open = l.match(/^\s*<IfModule\s+([\w.]+)>/)
    if (open) stack.push(open[1])
    else if (/^\s*<\/IfModule>/.test(l)) stack.pop()
    else if (/^\s*Header\b/.test(l)) expect(stack).toContain('mod_headers.c')
    else if (/^\s*SetEnvIf\b/.test(l)) expect(stack).toContain('mod_setenvif.c')
    else if (/^\s*AddType\b/.test(l)) expect(stack).toContain('mod_mime.c')
    else if (/^\s*Redirect/.test(l)) expect(stack).toContain('mod_alias.c')
  }
  expect(stack).toEqual([])
  expect(ht).toMatch(/AllowOverride FileInfo/)
  expect(fs.existsSync(path.resolve('build/client/assets/index.html'))).toBe(true)
})

test('old site pages (/about.html etc.) redirect to their new page, and every target exists', async () => {
  const ht = fs.readFileSync(path.resolve('build/client/.htaccess'), 'utf8')
  const rules = [...ht.matchAll(/^\s*RedirectMatch 301 \^\/([\w-]+)\\\.html\$ (\/(?:[\w-]+\/)?)$/gm)].map((m) => [m[1], m[2]])
  expect(rules.map(([from]) => from).sort()).toEqual([
    'about', 'contact', 'contact-us', 'covid-19', 'enterprises', 'example', 'facilities', 'innovations', 'media',
    'product', 'services', 'social-impact', 'team',
  ])
  const moved = { 'contact-us': '/contact/', example: '/' }
  for (const [from, to] of rules) {
    expect(to).toBe(moved[from] || `/${from}/`)
    expect(fs.existsSync(path.resolve(`build/client${to}index.html`)), to).toBe(true)
  }
  expect(ht).not.toMatch(/Redirect\w*\s+\d*\s*\^?\/index/) // would loop with DirectoryIndex
  expect(ht).toMatch(/^\s*RedirectMatch 410 \^\/mail\\\.php\$$/m) // the old contact script is gone
})

test('mobile menu opens from the header and closes on navigation', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Toggle navigation menu' }).click()
  const link = page.locator('#mobile-nav').getByRole('link', { name: 'Team' })
  await expect(link).toBeVisible()
  await link.click()
  await expect(page.locator('h1')).toHaveText('PI, Co-PIs and Research Team')
  await expect(page.locator('#mobile-nav')).toHaveCount(0)
})

test('frames come only from Google Maps and youtube-nocookie (what the CSP frame-src allows)', async ({ page }) => {
  for (const route of ['/', '/contact/', '/innovations/', '/enterprises/', '/covid-19/', '/social-impact/']) {
    await page.goto(route)
    const srcs = await page.locator('iframe').evaluateAll((els) => els.map((e) => e.getAttribute('src')))
    for (const src of srcs) expect(src).toMatch(/^https:\/\/(www\.google\.com\/maps\/embed|www\.youtube-nocookie\.com\/embed\/)/)
  }
})
