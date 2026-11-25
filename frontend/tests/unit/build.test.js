import fs from 'node:fs'
import { describe, expect, it } from 'vitest'
import { SnapshotGuardError, parsePrivacyNotice, validateSnapshot } from '../../app/snapshot.server.js'
import { PAGES, PAGE_NEEDS, REQUIRED, selectData } from '../../src/site/registry.js'
import { validateField, mailtoHref } from '../../src/site/components/ContactForm.jsx'
import { toRoute, uniqueItems, youtubeId, blocksFor } from '../../src/site/util.js'

const stub = JSON.parse(fs.readFileSync(process.env.SNAPSHOT_PATH || 'snapshot.json', 'utf8'))

describe('build guard', () => {
  it('accepts the dev snapshot', () => {
    expect(() => validateSnapshot(structuredClone(stub))).not.toThrow()
  })
  it.each(REQUIRED.collections)('fails when collection "%s" is missing (never an empty section)', (name) => {
    const snap = structuredClone(stub)
    delete snap.collections[name]
    expect(() => validateSnapshot(snap)).toThrow(SnapshotGuardError)
    expect(() => validateSnapshot(snap)).toThrow(new RegExp(name))
  })
  it.each(REQUIRED.singletons)('fails when singleton "%s" is missing', (name) => {
    const snap = structuredClone(stub)
    delete snap.singletons[name]
    expect(() => validateSnapshot(snap)).toThrow(SnapshotGuardError)
  })
  it('fails on an unknown schema version', () => {
    expect(() => validateSnapshot({ ...structuredClone(stub), schema_version: 2 })).toThrow(/schema_version/)
  })
  it('an empty (but present) collection is allowed: the section is hidden, not the build', () => {
    const snap = structuredClone(stub)
    snap.collections['media-events'] = []
    expect(() => validateSnapshot(snap)).not.toThrow()
  })
})

describe('registry', () => {
  it('has the 14 public pages, each with declared data needs', () => {
    expect(PAGES.map((p) => p.id)).toEqual(['home', 'about', 'team', 'innovations', 'facilities', 'services', 'product', 'enterprises', 'social-impact', 'covid-19', 'research', 'research-translation', 'media', 'contact'])
    for (const p of PAGES) expect(PAGE_NEEDS[p.id]).toBeTruthy()
  })
  it('selectData drops unpublished rows', () => {
    const d = selectData({ singletons: {}, collections: { 'team-members': [{ id: 1, name: 'A' }, { id: 2, name: 'Hidden', is_published: false }] } }, { singletons: [], collections: ['team-members'] })
    expect(d.collections['team-members'].map((m) => m.name)).toEqual(['A'])
  })
  it('selectData keeps the snapshot shape and only referenced media', () => {
    const d = selectData(stub, PAGE_NEEDS.team)
    expect(Object.keys(d.collections)).toEqual(['team-categories', 'team-members', 'page-heroes'])
    for (const url of Object.keys(d.media)) expect(JSON.stringify(d.collections)).toContain(url)
  })
})

describe('contact validation mirrors the relay', () => {
  it.each([
    ['name', '', 'Enter your name.'],
    ['name', 'A', 'at least 2'],
    ['email', 'x@', 'like name@example.com'],
    ['phone', 'abc', 'digits'],
    ['message', 'short', 'at least 10'],
  ])('%s=%j → error', (field, value, msg) => {
    expect(validateField(field, value)).toContain(msg)
  })
  it.each([
    ['name', 'Priya Das'],
    ['email', 'priya@example.com'],
    ['phone', ''],
    ['phone', '+91 88200-51894'],
    ['message', 'We would like to test a device prototype.'],
  ])('%s=%j → ok', (field, value) => expect(validateField(field, value)).toBe(''))
  it('mailto fallback carries the message', () => {
    const href = mailtoHref('office@example.org', { name: 'P', email: 'p@example.com', phone: '', message: 'Hello there team' })
    expect(href.startsWith('mailto:office@example.org?subject=')).toBe(true)
    expect(decodeURIComponent(href)).toContain('Hello there team')
  })
})

describe('privacy notice', () => {
  const md = `# x\n\n## Short notice (above)\n\n> We use it only to reply. [How we use your message](#privacy)\n\n## Full notice\n\n> ### How we use your message\n>\n> **Who we are.** Run by CRTDH. [confirm the name]\n>\n> **Your choices.** Ask us. Write to **[contact name]** at **[contact email]**. We reply within **30 days**.\n>\n> *Last updated: [date].*\n\n## Placeholders\n- x\n`
  it('keeps the short notice and its link', () => {
    expect(parsePrivacyNotice(md).short).toBe('We use it only to reply. [How we use your message](#privacy)')
  })
  it('drops sentences that still hold [placeholders]', () => {
    const r = parsePrivacyNotice(md)
    expect(r.title).toBe('How we use your message')
    expect(r.paragraphs).toEqual(['**Who we are.** Run by CRTDH.', '**Your choices.** Ask us. We reply within **30 days**.'])
  })
  it('returns null without a document', () => expect(parsePrivacyNotice(null)).toBeNull())
})

describe('utilities', () => {
  it('normalises nav urls', () => {
    expect(toRoute('about.html')).toBe('/about/')
    expect(toRoute('/')).toBe('/')
    expect(toRoute('index.html')).toBe('/')
    expect(toRoute('/media/')).toBe('/media/')
  })
  it('reads YouTube ids', () => {
    expect(youtubeId('https://www.youtube.com/watch?v=ZkZXzuaIeoQ')).toBe('ZkZXzuaIeoQ')
    expect(youtubeId('https://youtu.be/abc12345')).toBe('abc12345')
  })
  it('drops duplicate gallery rows and duplicate blocks', () => {
    expect(uniqueItems([{ image: 'a' }, { image: 'a' }, { image: 'b' }])).toHaveLength(2)
    expect(blocksFor([{ id: 1, page: 'x', section_title: 'A' }, { id: 2, page: 'x', section_title: 'a' }, { id: 3, page: 'y' }], 'x')).toHaveLength(1)
  })
})

describe('previous design, built from the snapshot', async () => {
  const React = await import('react')
  const { renderToStaticMarkup } = await import('react-dom/server')
  const { pages, Layout } = await import('../../src/site/index.js')
  const data = (page) => selectData(structuredClone(stub), { singletons: [...PAGE_NEEDS[page].singletons, 'site-settings'], collections: [...PAGE_NEEDS[page].collections, 'nav-items'] })
  const render = (id) => renderToStaticMarkup(React.createElement(Layout, { data: data(id), currentPath: PAGES.find((p) => p.id === id).path },
    React.createElement(pages[id], { data: data(id) })))

  it.each(PAGES.map((p) => p.id))('%s renders complete HTML with no loading state and no network call', (id) => {
    const calls = []
    const realFetch = globalThis.fetch
    globalThis.fetch = (...a) => { calls.push(a); return Promise.reject(new Error('no network in a pre-built page')) }
    try {
      const html = render(id)
      expect(html).toContain('site-header')
      expect(html).toContain('site-footer')
      expect(html).not.toContain('class="spinner"')
      expect(html).not.toMatch(/Couldn.t load this content/)
      expect(calls).toHaveLength(0)
    } finally {
      globalThis.fetch = realFetch
    }
  })
  it('Home shows the hero, the four figures and the membership and visit sections', () => {
    const html = render('home')
    for (const s of ['home.hero', 'home.membership', 'home.objective', 'home.visit']) expect(html).toContain(`data-block="${s}"`)
    for (const label of ['Innovations developed', 'Enterprises incubated', 'Researchers &amp; staff', 'Years sponsored by DSIR']) expect(html).toContain(label)
  })
  it('the menu marks the current page and links carry the trailing slash', () => {
    const html = render('team')
    expect(html).toMatch(/<a[^>]*href="\/team\/"[^>]*aria-current="page"|<a[^>]*aria-current="page"[^>]*href="\/team\/"/)
  })
  it('frames only Google Maps and YouTube (the CSP frame-src lists only what pages use)', () => {
    const snap = structuredClone(stub)
    snap.singletons['site-settings'].map_embed_url = 'https://evil.example/frame'
    snap.collections['video-blocks'] = [{ id: 1, page: 'enterprises', title: 'v', youtube_url: 'https://evil.example/x', is_published: true }]
    const d = selectData(snap, { singletons: ['site-settings', 'home-page'], collections: ['enterprises', 'image-grid-blocks', 'video-blocks', 'nav-items'] })
    const html = renderToStaticMarkup(React.createElement(Layout, { data: d }, React.createElement(pages.enterprises, { data: d })))
    expect(html).not.toContain('evil.example')
    const contact = renderToStaticMarkup(React.createElement(pages.contact, { data: d }))
    expect(contact).not.toContain('<iframe')
  })
  it('unsafe links from content render as text', () => {
    const snap = structuredClone(stub)
    snap.singletons['site-settings'].facebook_url = 'javascript:alert(1)'
    const d = selectData(snap, { singletons: ['site-settings'], collections: ['nav-items'] })
    expect(renderToStaticMarkup(React.createElement(Layout, { data: d }, 'x'))).not.toContain('javascript:')
  })
})
