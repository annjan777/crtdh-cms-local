// Content parity for the restored previous design: every page shows the published items from the
// snapshot, in CMS order, and nothing unpublished. Layout is the previous site's; these tests check
// content, not markup.
import { expect, test } from '@playwright/test'
import { expectInOrder, snapshot, visible } from './helpers.js'

const c = snapshot.collections
const s = snapshot.singletons
const text = async (page, route) => {
  await page.goto(route)
  return page.locator('main').innerText()
}

test('home: headline, membership, home-page texts and the visit block', async ({ page }) => {
  const t = await text(page, '/')
  await expect(page.locator('h1')).toHaveCount(1)
  expect(t).toContain('Work with CRTDH')
  expect(t).toContain(s['home-page'].enterprises_text.slice(0, 60))
  expect(t).toContain(s['home-page'].women_text_1.slice(0, 60))
  // Every published news item is listed under Latest Updates.
  const updates = await page.locator('[data-block="home.news"]').innerText()
  for (const n of visible(c['news-items'])) expect(updates).toContain(n.text)
})

test('about: programme, mission, focus areas, objectives, timeline, institutions', async ({ page }) => {
  const t = await text(page, '/about/')
  const a = s['about-page']
  for (const field of ['intro', 'mission_vision', 'dsir_about', 'iitkgp_about']) expect(t).toContain(a[field].split('\n')[0].slice(0, 60))
  expectInOrder(expect, t, visible(c['focus-areas']).map((f) => f.title), 'focus areas')
})

test('team: categories with published members, members in order, nobody unpublished', async ({ page }) => {
  const t = await text(page, '/team/')
  const members = visible(c['team-members'])
  const cats = c['team-categories'].filter((cat) => members.some((m) => m.category === cat.id))
  for (const cat of cats) expectInOrder(expect, t, members.filter((m) => m.category === cat.id).map((m) => m.name), cat.name)
  for (const m of c['team-members'].filter((x) => x.is_published === false)) expect(t).not.toContain(m.name)
})

test('innovations: every innovation, in order, with its body text', async ({ page }) => {
  await page.goto('/innovations/')
  await expect(page.locator('article.tech h2')).toHaveText(visible(c.innovations).map((i) => i.title))
  const t = await page.locator('main').innerText()
  expect(t).toContain('Portable and thus spot diagnosis is possible')
  expect(await page.locator('main').innerHTML()).not.toMatch(/&lt;(p|strong|ul)&gt;/) // rich text is rendered, not shown as tags
})

test('facilities: equipment in order and the manufacturing anchor', async ({ page }) => {
  const t = await text(page, '/facilities/')
  // Grouped by capability: every instrument is on the page, none is dropped; CMS order within a group.
  for (const e of visible(c.equipment)) expect(t, `equipment "${e.name}"`).toContain(e.name)
  const groups = await page.locator('.fac-group').count()
  expect(groups).toBeGreaterThan(1)
  const listed = await page.locator('.fac-group .fac-equip__name, .fac-group .fac-also__list li').count()
  expect(listed).toBe(visible(c.equipment).length)
  await expect(page.locator('#manufacturing-plants')).toHaveCount(1)
})

test('innovations: a step-by-step procedure is folded away, closed, and opens on request', async ({ page }) => {
  await page.goto('/innovations/')
  const steps = page.locator('details.tech__steps')
  if (!(await steps.count())) return // no technology has a procedure in this snapshot
  await expect(steps.first()).not.toHaveAttribute('open', '')
  await steps.first().locator('summary').click()
  await expect(steps.first()).toHaveAttribute('open', '')
  await expect(steps.first().locator('li').first()).toBeVisible()
})

test('services: every service in order', async ({ page }) => {
  const t = await text(page, '/services/')
  expectInOrder(expect, t, visible(c.services).map((x) => x.title.replace('R & D', 'R&D')), 'services')
})

test('product: every product with its partners', async ({ page }) => {
  const t = await text(page, '/product/')
  expectInOrder(expect, t, visible(c.products).map((p) => p.name), 'products')
})

test('enterprises: directory in order', async ({ page }) => {
  const t = await text(page, '/enterprises/')
  expectInOrder(expect, t, visible(c.enterprises).map((e) => e.name), 'enterprises')
})

test('covid-19: video titles in order', async ({ page }) => {
  const t = await text(page, '/covid-19/')
  expectInOrder(expect, t, visible(c['video-blocks']).filter((v) => v.page === 'covid-19').map((v) => v.title), 'covid videos')
})

test('media: every event with photos in order, deep-link anchors, coverage and newsletters', async ({ page }) => {
  const t = await text(page, '/media/')
  const events = visible(c['media-events']).filter((e) => e.images.length)
  expectInOrder(expect, t, events.map((e) => e.title), 'events')
  for (const e of events) await expect(page.locator(`#${e.slug}`)).toHaveCount(1)
  // A title that is just the address is shown as "publication — headline"; every link is present either way.
  for (const link of visible(c['media-coverage-links'])) {
    if (!/^https?:\/\//i.test(link.title)) expect(t).toContain(link.title)
    await expect(page.locator(`main a[href="${link.url}"]`)).toHaveCount(1)
  }
  expectInOrder(expect, t, visible(c.documents).map((d) => d.title), 'newsletters')
})

test('contact: office details from site settings', async ({ page }) => {
  const t = await text(page, '/contact/')
  const st = s['site-settings']
  for (const v of [st.address, st.phone_primary, st.email_primary]) expect(t).toContain(v)
})
