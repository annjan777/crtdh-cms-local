#!/usr/bin/env node
// Static preview of build/client that behaves like the CIC host: directory index.html,
// /media/* from MEDIA_ROOT, unknown paths → 404.html with status 404.
// Usage: PORT=3100 MEDIA_ROOT=../backend/media node scripts/serve.mjs
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'

const root = path.resolve(process.env.BUILD_DIR || 'build/client')
const mediaRoot = path.resolve(process.env.MEDIA_ROOT || '/home/claude/crtdh-cms-local/backend/media')
const port = Number(process.env.PORT || 3100)
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.data': 'text/x-script', '.xml': 'application/xml', '.txt': 'text/plain', '.woff2': 'font/woff2',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif',
  '.gif': 'image/gif', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.pdf': 'application/pdf',
}

function resolve(urlPath) {
  const clean = decodeURIComponent(urlPath.split('?')[0])
  if (clean.startsWith('/media/')) {
    const f = path.join(mediaRoot, clean.slice('/media/'.length))
    return f.startsWith(mediaRoot) ? f : null
  }
  let f = path.join(root, clean)
  if (!f.startsWith(root)) return null
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html')
  return f
}

http
  .createServer((req, res) => {
    const f = resolve(req.url)
    if (f && fs.existsSync(f) && fs.statSync(f).isFile()) {
      const ext = path.extname(f).toLowerCase()
      res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream', 'Cache-Control': 'no-cache' })
      fs.createReadStream(f).pipe(res)
      return
    }
    res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' })
    fs.createReadStream(path.join(root, '404.html')).pipe(res)
  })
  .listen(port, () => console.log(`serving ${root} (+ /media from ${mediaRoot}) on http://localhost:${port}`))
