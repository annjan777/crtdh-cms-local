import fs from 'node:fs'
import { describe, expect, it } from 'vitest'
import { SnapshotGuardError, parsePrivacyNotice, validateSnapshot } from '../../app/snapshot.server.js'
import { PAGES, PAGE_NEEDS, REQUIRED, selectData } from '../../src/site/registry.js'
import { groupNav } from '../../src/site/components/Layout.jsx'
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
  it('has the 12 public pages, each with declared data needs', () => {
    expect(PAGES.map((p) => p.id)).toEqual(['home', 'about', 'team', 'innovations', 'facilities', 'services', 'product', 'enterprises', 'social-impact', 'covid-19', 'media', 'contact'])
    for (const p of PAGES) expect(PAGE_NEEDS[p.id]).toBeTruthy()
  })
  it('selectData keeps the snapshot shape and only referenced media', () => {
    const d = selectData(stub, PAGE_NEEDS.team)
    expect(Object.keys(d.collections)).toEqual(['team-categories', 'team-members'])
    for (const url of Object.keys(d.media)) expect(JSON.stringify(d.collections)).toContain(url)
  })
})

describe('navigation grouping', () => {
  it('groups the CMS nav items as About · Our work · Impact · News and keeps every item', () => {
    const { groups, contact } = groupNav(stub.collections['nav-items'])
    expect(groups.map((g) => g.label)).toEqual(['About', 'Our work', 'Impact', 'News'])
    const routes = groups.flatMap((g) => g.items.map((i) => i.route))
    expect(routes.length + 1).toBe(stub.collections['nav-items'].length - 1) // all but Home, plus Contact
    expect(contact.route).toBe('/contact/')
  })
  it('an unknown CMS item still appears (under About)', () => {
    const { groups } = groupNav([...stub.collections['nav-items'], { id: 99, label: 'Careers', url: '/careers' }])
    expect(groups.find((g) => g.id === 'about').items.map((i) => i.label)).toContain('Careers')
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

describe('Home figures strip (owner decision D10)', async () => {
  const { homeFigures, DSIR_YEARS } = await import('../../src/site/pages/Home.jsx')
  it('counts published innovations, enterprises and team members like the old Home did, plus the DSIR years', () => {
    const c = { innovations: [{ id: 1 }, { id: 2, is_published: false }, { id: 3 }], enterprises: [{ id: 1 }],
      'team-members': [{ id: 1 }, { id: 2 }, { id: 3, is_published: false }] }
    expect(homeFigures(c)).toEqual([
      { value: 2, label: 'Innovations developed' },
      { value: 1, label: 'Enterprises incubated' },
      { value: 2, label: 'Researchers & staff' },
      { value: DSIR_YEARS, label: 'Years sponsored by DSIR' },
    ])
    expect(DSIR_YEARS).toBe(8)
  })
  it('drops a figure that would read 0+', () => {
    expect(homeFigures({ innovations: [], enterprises: [] }).map((f) => f.label)).toEqual(['Years sponsored by DSIR'])
  })
})

describe('owner content kept from the old site (decision D13)', async () => {
  const React = await import('react')
  const { renderToStaticMarkup } = await import('react-dom/server')
  const { default: Home, EXPLORE, CAPTIONS } = await import('../../src/site/pages/Home.jsx')
  const { default: Team, PI_LINE, TEAM_TAGLINE, isPrincipal } = await import('../../src/site/pages/Team.jsx')
  const data = (page) => selectData(structuredClone(stub), { singletons: [...PAGE_NEEDS[page].singletons, 'site-settings'], collections: [...PAGE_NEEDS[page].collections, 'nav-items'] })
  const text = (html) => html.replace(/<!-- -->/g, '').replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&amp;/g, '&').replace(/\s+/g, ' ')

  it('Home: four figures, the three Explore lines with their links, the four photo captions', () => {
    const html = renderToStaticMarkup(React.createElement(Home, { data: data('home') }))
    const t = text(html)
    for (const label of ['Innovations developed', 'Enterprises incubated', 'Researchers & staff', 'Years sponsored by DSIR']) expect(t).toContain(label)
    for (const e of EXPLORE) {
      expect(t).toContain(e.text)
      expect(html).toContain(`href="${e.to}"`)
    }
    expect(EXPLORE.map((e) => e.title)).toEqual(['Innovations', 'Enterprises', 'Social Impact'])
    for (const caption of Object.values(CAPTIONS)) expect(html).toContain(`<figcaption>${caption}</figcaption>`)
  })
  it('Team: the PI line, the heading, the tagline and Get in Touch to the contact page', () => {
    const t = text(renderToStaticMarkup(React.createElement(Team, { data: data('team') })))
    expect(t).toContain(`${PI_LINE.title} — ${PI_LINE.text}`)
    expect(PI_LINE.text).toBe("Guiding CRTDH's vision for affordable healthcare technologies.")
    expect(t).toContain('A multidisciplinary team working towards innovative healthcare solutions')
    expect(t).toContain(TEAM_TAGLINE)
    expect(t).toContain('Get in Touch')
    expect(isPrincipal('Principal Investigator') && !isPrincipal('Co-Principal Investigator')).toBe(true)
  })
})
