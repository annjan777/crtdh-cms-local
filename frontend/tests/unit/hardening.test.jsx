// Review fixes: contact form never rendered without JavaScript, trailing-slash URLs, safe hrefs, hex-only
// LQIP colours, rich text through the allow-list, and the Home/footer design fixes.
import fs from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { PAGES } from '../../src/site/registry.js'
import { SEO } from '../../src/site/seo.js'
import { safeColor, safeHref, toRoute, withSlash } from '../../src/site/util.js'
import { sanitizeRichText } from '../../src/site/richtext.js'
import SiteLink, { PlainLink } from '../../src/site/link.jsx'
import { MediaProvider, Img } from '../../src/site/media.jsx'
import RichText from '../../src/site/components/RichText.jsx'
import ContactForm from '../../src/site/components/ContactForm.jsx'

const snap = JSON.parse(fs.readFileSync(process.env.SNAPSHOT_PATH || 'snapshot.json', 'utf8'))
const html = (el) => renderToStaticMarkup(el)

describe('contact form without JavaScript', () => {
  it('server/prerender output has no <form>, only mailto and tel links', () => {
    const out = html(<ContactForm email="office@example.org" phone="+91 88200 51894" notice={<p id="contact-notice">n</p>} />)
    expect(out).not.toMatch(/<form\b|<input\b|<textarea\b/)
    expect(out).toContain('href="mailto:office@example.org?subject=')
    expect(out).toContain('href="tel:+918820051894"')
    expect(out).toContain('id="contact-notice"')
  })
  it('without email or phone it still says what to do', () => {
    expect(html(<ContactForm />)).toContain('needs JavaScript')
  })
})

describe('trailing slashes', () => {
  it('every public page path, SEO path and sitemap source ends with "/"', () => {
    for (const p of PAGES) expect(p.path).toMatch(/\/$/)
    for (const [id, s] of Object.entries(SEO)) if (id !== 'notfound') expect(s.path).toMatch(/\/$/)
  })
  it('toRoute and withSlash give the canonical form; files, anchors and queries keep theirs', () => {
    expect(toRoute('about.html')).toBe('/about/')
    expect(toRoute('/team')).toBe('/team/')
    expect(toRoute('/')).toBe('/')
    expect(withSlash('/about')).toBe('/about/')
    expect(withSlash('/innovations#innovation-3')).toBe('/innovations/#innovation-3')
    expect(withSlash('/media/?x=1')).toBe('/media/?x=1')
    expect(withSlash('/_media/doc.pdf')).toBe('/_media/doc.pdf')
    expect(withSlash('#top')).toBe('#top')
    expect(withSlash('https://example.org/a')).toBe('https://example.org/a')
  })
  it('SiteLink writes the slash for site pages', () => {
    expect(html(<SiteLink to="/facilities#manufacturing-plants">x</SiteLink>)).toContain('href="/facilities/#manufacturing-plants"')
  })
})

describe('safeHref', () => {
  it.each(['/', '/about/', '#privacy', 'https://example.org/x', 'http://example.org', 'mailto:a@b.in', 'tel:+911234'])('allows %s', (h) => {
    expect(safeHref(h)).toBe(h)
  })
  it.each([
    'javascript:alert(1)', ' JavaScript:alert(1)', 'java\tscript:alert(1)', 'data:text/html,<b>', 'vbscript:x', '//evil.example/x',
    '/\\evil.example', 'about.html', 'foo:bar', '', null, 42, '​javascript:alert(1)',
  ])('refuses %j', (h) => {
    expect(safeHref(h)).toBeNull()
  })
  it('unsafe snapshot links render as text, not links', () => {
    expect(html(<SiteLink to="javascript:alert(1)">news</SiteLink>)).toBe('<span>news</span>')
    expect(html(<PlainLink href="data:text/html,x" className="rows__link">doc</PlainLink>)).toBe('<span class="rows__link">doc</span>')
    expect(html(<PlainLink href="/_media/a.pdf" download>doc</PlainLink>)).toBe('<a href="/_media/a.pdf" download="">doc</a>')
  })
})

describe('LQIP colour', () => {
  const render = (lqip) => html(<MediaProvider media={{ '/_media/a.jpg': { width: 10, height: 10, lqip } }}><Img src="/_media/a.jpg" alt="" /></MediaProvider>)
  it('uses a hex colour', () => {
    expect(safeColor('#a1b2c3')).toBe('#a1b2c3')
    expect(render('#a1b2c3')).toContain('background-color:#a1b2c3')
  })
  it.each(['url(https://evil.example/x.png)', 'red;background:url(x)', 'data:image/png;base64,AAAA', 'rgb(1,2,3)', '#12345'])('ignores %s', (v) => {
    expect(render(v)).not.toContain('background')
  })
})

describe('rich text', () => {
  it('keeps the allow-list and drops everything else', () => {
    const out = sanitizeRichText(
      '<p class="x" onclick="a()">Hi <strong>there</strong> <img src=x onerror=alert(1)><script>alert(1)</script><style>p{}</style></p><h2>Big</h2><h3>Small</h3><ul><li>a<li>b</ul><!-- c -->',
    )
    expect(out).toBe('<p>Hi <strong>there</strong> </p>Big<h3>Small</h3><ul><li>a<li>b</li></li></ul>')
  })
  it('links keep only a safe href', () => {
    expect(sanitizeRichText('<a href="https://ex.org/?a=1&b=2" target="_blank" onmouseover="x">ok</a>')).toBe('<a href="https://ex.org/?a=1&amp;b=2" rel="noopener noreferrer">ok</a>')
    expect(sanitizeRichText('<a href="javascript:alert(1)">x</a>')).toBe('<a>x</a>')
    expect(sanitizeRichText('<a href="&#106;avascript&#58;alert(1)">x</a>')).toBe('<a>x</a>')
    expect(sanitizeRichText('<a href="jav&#x09;ascript:alert(1)">x</a>')).toBe('<a>x</a>')
    expect(sanitizeRichText("<a href='//evil.example'>x</a>")).toBe('<a>x</a>')
  })
  it('escapes stray markup and closes what was left open', () => {
    expect(sanitizeRichText('a < b > c & d <em>open')).toBe('a &lt; b &gt; c &amp; d <em>open</em>')
    expect(sanitizeRichText('<scr<script>ipt>alert(1)</script>')).toBe('&lt;scr')
    expect(sanitizeRichText('<p>x</em></p>')).toBe('<p>x</p>')
  })
  it('RichText shows plain text as paragraphs and markup through the sanitiser', () => {
    expect(html(<RichText html={'R&D first.\n\nSecond <3'} className="prose-block" />)).toBe('<div class="prose-block"><p>R&amp;D first.</p><p>Second &lt;3</p></div>')
    expect(html(<RichText html="<p>One <b>bold</b></p><script>x()</script>" />)).toBe('<div class=""><p>One <b>bold</b></p></div>')
  })
  it('the About page renders every registry richtext field through RichText', () => {
    const src = fs.readFileSync('src/site/pages/About.jsx', 'utf8')
    for (const f of ['intro', 'mission_vision', 'dsir_about', 'iitkgp_about']) expect(src).toContain(`<ProseBlock text={about.${f}}`)
    expect(src).toMatch(/function ProseBlock\(\{ text \}\) \{\n  return <RichText html=\{text\}/)
    expect(fs.readFileSync('src/site/pages/Innovations.jsx', 'utf8')).toContain('<RichText html={innovation.body}')
    for (const f of fs.readdirSync('src/site/pages')) {
      if (f.endsWith('.jsx')) expect(fs.readFileSync(`src/site/pages/${f}`, 'utf8')).not.toContain('dangerouslySetInnerHTML')
    }
  })
})
