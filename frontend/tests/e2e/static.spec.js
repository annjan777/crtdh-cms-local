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
      expect(html).toMatch(/<h1[^>]*>[^<]+/)
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
      await expect(page.locator('main#main')).toHaveCount(1)
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
    const fams = await page.evaluate(() => [...document.querySelectorAll('body *')].map((el) => getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim()))
    fams.forEach((f) => used.add(f))
  }
  expect([...used].filter((f) => !['Fraunces', 'Open Sans', 'Montserrat'].includes(f))).toEqual([])
})

test('unknown paths get the designed 404 (status 404) and it hydrates without errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  const res = await page.goto('/no/such/page', { waitUntil: 'networkidle' })
  expect(res.status()).toBe(404)
  await expect(page.locator('h1')).toHaveText('This page is not on the site')
  await page.getByLabel('Search the site’s pages').fill('anemia')
  await expect(page.locator('.notfound__links .rows li')).not.toHaveCount(12)
  await page.getByRole('link', { name: 'Go to the home page' }).click()
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
  await expect(page.locator('h1')).toHaveText('Our team')
  await page.locator('footer').getByRole('link', { name: 'Innovations' }).click()
  await expect(page.locator('h1')).toHaveText('Innovations')
  expect(bad).toEqual([])
})

test('hero: at most 4 slides, first is eager LCP image, pause control; reduced motion does not autoplay', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto('/')
  const slides = page.locator('.hero__slide')
  expect(await slides.count()).toBeLessThanOrEqual(4)
  await expect(slides.first().locator('img')).toHaveAttribute('fetchpriority', 'high')
  await expect(slides.first().locator('img')).toHaveAttribute('loading', 'eager')
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeVisible() // not playing under reduced motion
  await page.waitForTimeout(8500)
  await expect(page.locator('.hero__count')).toHaveText(/Photograph 1 of/)
  await page.getByRole('button', { name: 'Next photograph' }).click()
  await expect(page.locator('.hero__count')).toHaveText(/Photograph 2 of/)
  await ctx.close()
})

test('hero autoplay holds at least 7 s and can be paused', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible()
  await page.mouse.move(5, 600) // away from the hero
  await page.waitForTimeout(6500)
  await expect(page.locator('.hero__count')).toHaveText(/Photograph 1 of/)
  await page.getByRole('button', { name: 'Pause' }).click()
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeVisible()
})

test('mobile menu opens full screen with 48px rows and closes on navigation', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto('/')
  await page.locator('.mnav__toggle').click()
  const link = page.locator('.mnav__panel').getByRole('link', { name: 'Team' })
  await expect(link).toBeVisible()
  expect((await link.boundingBox()).height).toBeGreaterThanOrEqual(48)
  await link.click()
  await expect(page.locator('h1')).toHaveText('Our team')
  await expect(page.locator('.mnav__panel')).toBeHidden()
})

test('contact map and videos load third-party frames only when pressed', async ({ page }) => {
  await page.route('https://www.google.com/**', (route) => route.fulfill({ status: 200, contentType: 'text/html', body: '<p>map</p>' }))
  await page.goto('/contact/')
  await expect(page.locator('iframe')).toHaveCount(0)
  const show = page.getByRole('button', { name: 'Show the map' })
  if (await show.count()) {
    await show.click()
    await expect(page.locator('.map iframe')).toHaveAttribute('src', /^https:\/\/www\.google\.com\/maps\/embed/)
  }
  await page.goto('/')
  await expect(page.locator('iframe')).toHaveCount(0)
  await expect(page.locator('img[src^="http"]')).toHaveCount(0)
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
  }
  expect(stack).toEqual([])
  expect(ht).toMatch(/AllowOverride FileInfo/)
  expect(fs.existsSync(path.resolve('build/client/assets/index.html'))).toBe(true)
})

test('home video posters and facility tiles are never empty boxes', async ({ page }) => {
  await page.goto('/')
  const posters = page.locator('.news__videos .video__poster')
  for (let i = 0; i < (await posters.count()); i++) {
    const p = posters.nth(i)
    const cls = await p.getAttribute('class')
    expect(cls).toMatch(/video__poster--(photo|type)/)
    if (cls.includes('--photo')) await expect(p.locator('img')).toHaveCount(1)
    await expect(p.locator('.video__title')).not.toBeEmpty()
  }
  const tiles = page.locator('.facility-list__item')
  expect(await tiles.count()).toBeGreaterThan(0)
  for (let i = 0; i < (await tiles.count()); i++) {
    const t = tiles.nth(i)
    const cls = await t.getAttribute('class')
    if (cls.includes('--photo')) {
      await t.scrollIntoViewIfNeeded()
      await expect(t.locator('img')).toBeVisible()
      await expect.poll(() => t.locator('img').evaluate((img) => img.complete && img.naturalWidth)).toBeGreaterThan(0)
    } else expect(cls).toContain('--type')
  }
})

test('footer column headings never repeat a link label in their column', async ({ page }) => {
  await page.goto('/')
  const cols = page.locator('.site-footer__nav > div')
  for (let i = 0; i < (await cols.count()); i++) {
    const h = (await cols.nth(i).locator('h2').innerText()).trim().toLowerCase()
    const labels = (await cols.nth(i).locator('a').allInnerTexts()).map((s) => s.trim().toLowerCase())
    expect(labels).not.toContain(h)
  }
})
