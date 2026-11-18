#!/usr/bin/env node
// Turn the team stub snapshot (absolute localhost:8000 URLs) into a contract-shaped
// dev snapshot: site-relative /_media/... URLs and a `media` map with real image sizes.
// Usage: node scripts/dev-snapshot.mjs [stub] [out]   (MEDIA_ROOT defaults to backend/seed_media)
import fs from 'node:fs'
import path from 'node:path'
import { mediaRoot as resolveMediaRoot } from './media-root.mjs'
import { imageSize } from './imagesize.mjs'

const stub = process.argv[2] || '/home/claude/team/stub-snapshot.json'
const out = process.argv[3] || 'snapshot.json'
const mediaRoot = resolveMediaRoot()

const raw = fs.readFileSync(stub, 'utf8').replace(/https?:\/\/localhost:\d+\/media\//g, '/_media/')
const snap = JSON.parse(raw)
snap.schema_version = snap.schema_version || 1
snap.snapshot_id = snap.snapshot_id || 'dev-stub'
snap.published_at = snap.published_at || '2026-11-19T00:00:00Z'

const media = {}
for (const m of raw.matchAll(/"(\/_media\/[^"]+)"/g)) {
  const url = m[1]
  if (media[url] || !/\.(jpe?g|png|gif|webp)$/i.test(url)) continue
  const size = imageSize(path.join(mediaRoot, url.replace(/^\/_media\//, '')))
  if (size) media[url] = { source: url.replace(/^\/_media\//, ''), ...size, variants: {} }
}
snap.media = media

// Rows whose image file does not exist cannot be published (the real snapshot builder
// hashes each file). Hide them here, as the CMS would have to, and say so.
for (const [name, rows] of Object.entries(snap.collections)) {
  for (const row of rows) {
    for (const key of ['image', 'photo']) {
      const url = row[key]
      if (typeof url === 'string' && url.startsWith('/_media/') && /\.(jpe?g|png|gif|webp)$/i.test(url) && !media[url]) {
        console.warn(`warning: ${name} id ${row.id}: ${key} ${url} is missing on disk; row hidden`)
        if ('is_published' in row) row.is_published = false
        else row[key] = null
      }
    }
  }
}
fs.writeFileSync(out, JSON.stringify(snap, null, 1))
console.log(`wrote ${out}: ${Object.keys(media).length} media entries`)
