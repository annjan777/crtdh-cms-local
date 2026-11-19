// Where the dev media files live: MEDIA_ROOT, else the repo's backend/seed_media (or the older backend/media).
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
export function mediaRoot() {
  if (process.env.MEDIA_ROOT) return path.resolve(process.env.MEDIA_ROOT)
  const candidates = [
    path.resolve(here, '../../backend/seed_media'),
    path.resolve(here, '../../backend/media'),
    '/home/claude/crtdh-cms-local/backend/seed_media',
    '/home/claude/crtdh-cms-local/backend/media',
  ]
  return candidates.find((d) => fs.existsSync(d)) || candidates[0]
}
