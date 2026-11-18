#!/usr/bin/env node
// Placeholder and broken-content sweep over the built site (PLAN WS2.11). Non-zero exit on any finding.
// Checks every built HTML page for: Lorem / TODO / sample / placeholder text, unfilled [placeholders],
// empty headings, images without alt, images that do not exist, internal links (and #anchors) to
// pages or ids that do not exist. MEDIA_ROOT: where /media/* files live for the check (optional).
import fs from 'node:fs'
import path from 'node:path'

const out = path.resolve(process.argv[2] || process.env.BUILD_DIR || 'build/client')
const mediaRoot = process.env.MEDIA_ROOT ? path.resolve(process.env.MEDIA_ROOT) : null
const BANNED = /\b(lorem|ipsum|todo|tbd|fixme|sample|placeholder|dummy|coming soon)\b/i
const BRACKET = /\[(?:[a-z][^\]\n]{2,60})\]/i

function htmlFiles(dir) {
  const res = []
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory() && e.name !== 'assets') res.push(...htmlFiles(p))
    else if (e.name.endsWith('.html')) res.push(p)
  }
  return res
}

const pages = new Map() // route → { file, html, ids }
for (const file of htmlFiles(out)) {
  const rel = '/' + path.relative(out, file).replace(/\\/g, '/')
  const route = rel === '/index.html' ? '/' : rel.replace(/\/index\.html$/, '').replace(/\.html$/, '')
  const html = fs.readFileSync(file, 'utf8')
  const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]))
  pages.set(route, { file, html, ids })
}

const findings = []
const add = (route, msg) => findings.push(`${route}: ${msg}`)
const decode = (s) => s.replace(/&amp;/g, '&').replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')

function visibleText(html) {
  return decode(
    html
      .replace(/<head[\s\S]*?<\/head>/i, ' ')
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' '),
  )
}

function fileExists(urlPath) {
  const clean = decodeURIComponent(urlPath.split(/[?#]/)[0])
  if (clean.startsWith('/media/')) {
    if (!mediaRoot) return true // media ships separately; checked only when MEDIA_ROOT is given
    return fs.existsSync(path.join(mediaRoot, clean.slice(7)))
  }
  return fs.existsSync(path.join(out, clean))
}

for (const [route, { html }] of pages) {
  const text = visibleText(html)
  const banned = text.match(BANNED)
  if (banned) add(route, `placeholder text "${banned[0]}" in: …${text.slice(Math.max(0, banned.index - 40), banned.index + 40).replace(/\s+/g, ' ')}…`)
  const br = text.match(BRACKET)
  if (br) add(route, `unfilled placeholder ${br[0]}`)
  for (const m of html.matchAll(/<(h[1-6])\b[^>]*>([\s\S]*?)<\/\1>/gi)) {
    if (!decode(m[2].replace(/<[^>]+>/g, '')).trim()) add(route, `empty <${m[1]}>`)
  }
  for (const m of html.matchAll(/<img\b[^>]*>/gi)) {
    const tag = m[0]
    if (!/\salt="/.test(tag)) add(route, `image without alt: ${tag.slice(0, 120)}`)
    const src = tag.match(/\ssrc="([^"]+)"/)?.[1]
    if (src && src.startsWith('/') && !src.startsWith('//') && !fileExists(src)) add(route, `missing image ${src}`)
  }
  for (const m of html.matchAll(/<a\b[^>]*\shref="([^"]+)"/gi)) {
    const href = decode(m[1])
    if (/^(https?:|mailto:|tel:|\/\/)/.test(href)) continue
    const [p, hash] = href.split('#')
    const targetRoute = p === '' ? route : p.replace(/\/$/, '') || '/'
    if (/\.\w{2,5}$/.test(targetRoute)) {
      if (!fileExists(targetRoute)) add(route, `link to missing file ${href}`)
      continue
    }
    const target = pages.get(targetRoute)
    if (!target) {
      add(route, `link to missing page ${href}`)
      continue
    }
    if (hash && !target.ids.has(decodeURIComponent(hash))) add(route, `link to missing anchor ${href}`)
  }
}

if (!pages.has('/404')) findings.push('404.html is missing')
const expected = ['/', '/about', '/team', '/innovations', '/facilities', '/services', '/product', '/enterprises', '/social-impact', '/covid-19', '/media', '/contact']
for (const r of expected) if (!pages.has(r)) findings.push(`${r}: page not built`)

if (findings.length) {
  console.error(`sweep: ${findings.length} finding(s)`)
  for (const f of findings) console.error(`  - ${f}`)
  process.exit(1)
}
console.log(`sweep: ${pages.size} pages clean (text, headings, alt, images, links, anchors${mediaRoot ? ', media' : ''})`)
