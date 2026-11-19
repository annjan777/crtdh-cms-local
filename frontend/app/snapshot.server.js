// Build-time only: reads the published snapshot for the route loaders.
// Never bundled for the browser (".server" module).
import fs from 'node:fs'
import path from 'node:path'
import { REQUIRED, LAYOUT_NEEDS, PAGE_NEEDS, selectData } from '../src/site/registry.js'

let cached = null

export class SnapshotGuardError extends Error {
  constructor(message) {
    super(`[snapshot guard] ${message}`)
    this.name = 'SnapshotGuardError'
  }
}

export function validateSnapshot(snap, file = 'snapshot') {
  if (!snap || typeof snap !== 'object') throw new SnapshotGuardError(`${file} is not a JSON object`)
  if (snap.schema_version !== 1) throw new SnapshotGuardError(`${file}: unsupported schema_version ${snap.schema_version}`)
  const missing = []
  for (const k of REQUIRED.singletons) if (!snap.singletons || !snap.singletons[k]) missing.push(`singleton "${k}"`)
  for (const k of REQUIRED.collections) {
    if (!snap.collections || !Array.isArray(snap.collections[k])) missing.push(`collection "${k}"`)
  }
  if (missing.length) {
    throw new SnapshotGuardError(`${file} is missing ${missing.join(', ')}. The build stops instead of publishing empty sections.`)
  }
  return snap
}

export function snapshotPath() {
  return path.resolve(process.env.SNAPSHOT_PATH || path.join(process.cwd(), 'snapshot.json'))
}

export function getSnapshot() {
  if (cached) return cached
  const file = snapshotPath()
  if (!fs.existsSync(file)) throw new SnapshotGuardError(`no snapshot at ${file} (set SNAPSHOT_PATH)`)
  cached = validateSnapshot(JSON.parse(fs.readFileSync(file, 'utf8')), file)
  return cached
}

export function loadLayout() {
  const snap = getSnapshot()
  return {
    ...selectData(snap, LAYOUT_NEEDS),
    meta: {
      snapshot_id: snap.snapshot_id || null,
      published_at: snap.published_at || null,
      site_url: (process.env.SITE_URL || 'https://crtdh.iitkgp.ac.in').replace(/\/$/, ''),
      og_image: firstHeroImage(snap),
      // The footer links to /contact#privacy only when the full notice is published.
      privacy_notice: Boolean(parsePrivacyNotice(readPrivacyNotice())?.paragraphs?.length),
    },
  }
}

export function loadPage(id) {
  const needs = PAGE_NEEDS[id]
  if (!needs) throw new SnapshotGuardError(`unknown page id "${id}"`)
  const data = selectData(getSnapshot(), needs)
  if (id === 'contact') data.extra = { privacy: parsePrivacyNotice(readPrivacyNotice()) }
  return data
}

function firstHeroImage(snap) {
  const slide = (snap.collections['hero-slides'] || []).find((s) => s.is_published !== false && s.image)
  return slide ? slide.image : null
}

// docs/privacy-notice.md is written by the security lane; until it exists the
// contact page states plainly what the form does with the message.
function readPrivacyNotice() {
  const candidates = [
    process.env.PRIVACY_NOTICE_PATH,
    path.resolve(process.cwd(), '../docs/privacy-notice.md'),
  ].filter(Boolean)
  for (const f of candidates) {
    if (fs.existsSync(f)) return fs.readFileSync(f, 'utf8')
  }
  return null
}

// docs/privacy-notice.md holds a "## Short notice" and a "## Full notice", each as a blockquote.
// Sentences that still carry an owner placeholder ("[contact email]") are left out of the
// public page (they are listed in docs/content-gaps.md) instead of being published half-filled.
export function parsePrivacyNotice(md) {
  if (!md) return null
  const section = (title) => {
    const m = md.match(new RegExp(`^## ${title}[^\\n]*\\n([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, 'm'))
    if (!m) return []
    return m[1]
      .split('\n')
      .filter((l) => l.startsWith('>'))
      .map((l) => l.replace(/^>\s?/, ''))
      .join('\n')
      .split(/\n{2,}/)
      .map((p) => p.replace(/\n/g, ' ').trim())
      .filter(Boolean)
  }
  const placeholder = /\[[^\]]+\](?!\()/
  const clean = (p) =>
    p
      .split(/(?<=[.!?])\s+(?=[A-Z*[])/)
      .filter((sentence) => !placeholder.test(sentence))
      .join(' ')
      .trim()
  const short = section('Short notice').map(clean).filter(Boolean)
  const full = section('Full notice')
  const title = (full.find((p) => p.startsWith('### ')) || '### How we use your message').replace(/^###\s*/, '')
  const paras = full
    .filter((p) => !p.startsWith('### '))
    .map(clean)
    .filter((p) => p && !/^\*[^*]*\*$/.test(p) && p.replace(/\*\*[^*]+\*\*/g, '').trim())
  return { short: short.join(' '), title, paragraphs: paras }
}
