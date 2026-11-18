// Golden content parity: every page shows the same items, in the same order, as the
// snapshot (the data the 19 Nov runtime SPA rendered). Intentional v3 differences are listed
// in DESIGN.md ("Content changes from the 19 Nov site") and asserted here explicitly.
import { expect, test } from '@playwright/test'
import { expectInOrder, snapshot, visible } from './helpers.js'

const c = snapshot.collections
const s = snapshot.singletons
const text = async (page, route) => {
  await page.goto(route)
  return page.locator('main').innerText()
}

test('home: headline, enterprises, partners, innovations, news, documents, visit', async ({ page }) => {
  const t = await text(page, '/')
  const slide = visible(c['hero-slides'])[0]
  await expect(page.locator('h1')).toHaveText([slide.heading, slide.highlight_heading, slide.heading_end].join(' '))
  expectInOrder(expect, t, c.enterprises.map((e) => e.name), 'enterprises')
  expectInOrder(expect, t, c.products.filter((p) => p.partners.length).map((p) => p.name), 'products')
  expectInOrder(expect, t, c.innovations.filter((i) => i.images?.[0]?.image).slice(0, 6).map((i) => i.title), 'innovations')
  expectInOrder(expect, t, c['news-items'].map((n) => n.text), 'news')
  expectInOrder(expect, t, c.documents.map((d) => d.title), 'documents')
  expect(t).toContain(s['home-page'].enterprises_text.slice(0, 60))
  expect(t).toContain(s['home-page'].women_text_1.slice(0, 60))
  expect(t).toContain(s['site-settings'].address)
  // v3: hero shows at most 4 published slides, in order (approved d3).
  const srcs = await page.locator('.hero__slide img').evaluateAll((els) => els.map((e) => e.getAttribute('src')))
  expect(srcs).toEqual(visible(c['hero-slides']).slice(0, 4).map((x) => x.image))
})

test('about: programme, mission, focus areas, objectives, timeline, institutions', async ({ page }) => {
  const t = await text(page, '/about')
  const a = s['about-page']
  for (const field of ['intro', 'mission_vision', 'dsir_about', 'iitkgp_about']) expect(t).toContain(a[field].split('\n')[0].slice(0, 60))
  expectInOrder(expect, t, c['focus-areas'].map((f) => f.title), 'focus areas')
  expectInOrder(expect, t, c['objective-rows'].map((r) => r.task), 'objectives')
  expectInOrder(expect, t, c['timeline-entries'].map((r) => r.title), 'timeline')
})

test('team: categories with published members, members in order', async ({ page }) => {
  const t = await text(page, '/team')
  const members = visible(c['team-members'])
  const cats = c['team-categories'].filter((cat) => members.some((m) => m.category === cat.id))
  await expect(page.locator('h2.team__cat')).toHaveText(cats.map((x) => x.name))
  for (const cat of cats) expectInOrder(expect, t, [cat.name, ...members.filter((m) => m.category === cat.id).map((m) => m.name)], cat.name)
  for (const m of c['team-members'].filter((x) => x.is_published === false)) expect(t).not.toContain(m.name)
})

test('innovations: every innovation, in order, with its body text', async ({ page }) => {
  await page.goto('/innovations')
  await expect(page.locator('article h2')).toHaveText(c.innovations.map((i) => i.title))
  const t = await page.locator('main').innerText()
  expectInOrder(expect, t, c['project-slides'].map((p) => p.title), 'project spotlight')
  expect(t).toContain('Portable and thus spot diagnosis is possible')
})

test('facilities: equipment in order and the manufacturing block (both anchors work)', async ({ page }) => {
  const t = await text(page, '/facilities')
  expectInOrder(expect, t, c.equipment.map((e) => e.name), 'equipment')
  for (const b of c['image-grid-blocks'].filter((x) => x.page === 'facilities')) expect(t).toContain(b.section_title)
  await expect(page.locator('#manufacturingplants')).toHaveCount(1)
  await expect(page.locator('#manufacturing-plants')).toHaveCount(1)
})

test('services: every service in order', async ({ page }) => {
  const t = await text(page, '/services')
  expectInOrder(expect, t, c.services.map((x) => x.title.replace('R & D', 'R&D')), 'services')
})

test('product: every product with its partners', async ({ page }) => {
  const t = await text(page, '/product')
  expectInOrder(expect, t, c.products.flatMap((p) => [p.name, ...p.partners.map((x) => x.name)]), 'products')
})

test('enterprises: directory in order, engagement text, training block', async ({ page }) => {
  const t = await text(page, '/enterprises')
  expectInOrder(expect, t, c.enterprises.map((e) => e.name), 'enterprises')
  for (const b of c['image-grid-blocks'].filter((x) => x.page === 'enterprises')) expect(t).toContain(b.section_title)
})

test('social impact and covid-19: blocks, photos and videos', async ({ page }) => {
  let t = await text(page, '/social-impact')
  for (const b of c['image-grid-blocks'].filter((x) => x.page === 'social-impact')) {
    expect(t).toContain(b.section_title)
    const unique = new Set(b.items.map((i) => `${i.image}|${i.caption}`)).size
    await expect(page.locator(`#block-${b.id}`).locator('xpath=ancestor::section').locator('.gallery__item')).toHaveCount(unique)
  }
  t = await text(page, '/covid-19')
  expectInOrder(expect, t, c['video-blocks'].filter((v) => v.page === 'covid-19').map((v) => v.title), 'covid videos')
})

test('media: every event with photos, in order, deep-link anchors, coverage, newsletters', async ({ page }) => {
  await page.goto('/media')
  const events = c['media-events'].filter((e) => e.images.length)
  await expect(page.locator('section.event h2')).toHaveText(events.map((e) => e.title))
  for (const e of events) await expect(page.locator(`#${e.slug}`)).toHaveCount(1)
  await expect(page.locator('#press .rows li')).toHaveCount(c['media-coverage-links'].length)
  const t = await page.locator('main').innerText()
  expectInOrder(expect, t, c.documents.map((d) => d.title), 'newsletters')
  // All of an event's photos are in the page; the first six show until "Show all".
  const big = events.find((e) => e.images.length > 6)
  const sec = page.locator(`#${big.slug}`)
  await sec.getByRole('button', { name: /Show all/ }).click()
  await expect(sec.locator('.gallery__item')).toHaveCount(new Set(big.images.map((i) => `${i.image}|${i.caption}`)).size)
  await sec.locator('.gallery__item').first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeHidden()
})

test('contact: office details from site settings', async ({ page }) => {
  const t = await text(page, '/contact')
  const st = s['site-settings']
  for (const v of [st.address, st.phone_primary, st.email_primary]) expect(t).toContain(v)
})
