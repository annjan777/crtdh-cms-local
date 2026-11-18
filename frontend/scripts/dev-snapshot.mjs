#!/usr/bin/env node
// Turn the team stub snapshot (absolute localhost:8000 URLs) into a contract-shaped
// dev snapshot: site-relative /media/... URLs and a `media` map with real image sizes.
// Usage: node scripts/dev-snapshot.mjs [stub] [out]   (MEDIA_ROOT = backend/media)
import fs from 'node:fs'
import path from 'node:path'
import { imageSize } from './imagesize.mjs'

const stub = process.argv[2] || '/home/claude/team/stub-snapshot.json'
const out = process.argv[3] || 'snapshot.json'
const mediaRoot = process.env.MEDIA_ROOT || '/home/claude/crtdh-cms-local/backend/media'

const raw = fs.readFileSync(stub, 'utf8').replace(/https?:\/\/localhost:\d+\/media\//g, '/media/')
const snap = JSON.parse(raw)
snap.schema_version = snap.schema_version || 1
snap.snapshot_id = snap.snapshot_id || 'dev-stub'
snap.published_at = snap.published_at || '2026-11-19T00:00:00Z'

const media = {}
for (const m of raw.matchAll(/"(\/media\/[^"]+)"/g)) {
  const url = m[1]
  if (media[url] || !/\.(jpe?g|png|gif|webp)$/i.test(url)) continue
  const size = imageSize(path.join(mediaRoot, url.replace(/^\/media\//, '')))
  if (size) media[url] = { source: url.replace(/^\/media\//, ''), ...size, variants: {} }
}
snap.media = media
fs.writeFileSync(out, JSON.stringify(snap, null, 1))
console.log(`wrote ${out}: ${Object.keys(media).length} media entries`)
