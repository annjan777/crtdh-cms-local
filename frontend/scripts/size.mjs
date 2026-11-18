#!/usr/bin/env node
// JS budget (PLAN WS2.4): JS loaded by Home ≤ 150 KB gzip. Also reports every page.
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'
import { PAGES } from '../src/site/registry.js'

const out = path.resolve(process.env.BUILD_DIR || 'build/client')
const BUDGET_KB = Number(process.env.JS_BUDGET_KB || 150)
const gz = (f) => zlib.gzipSync(fs.readFileSync(f), { level: 9 }).length

function jsFor(htmlFile) {
  const html = fs.readFileSync(htmlFile, 'utf8')
  const files = new Set()
  for (const m of html.matchAll(/(?:src|href)="(\/assets\/[^"]+\.js)"/g)) files.add(m[1])
  for (const m of html.matchAll(/import\("(\/assets\/[^"]+\.js)"\)/g)) files.add(m[1])
  for (const m of html.matchAll(/import \* as \w+ from "(\/assets\/[^"]+\.js)"/g)) files.add(m[1])
  return [...files]
}

let failed = false
const rows = []
for (const p of [...PAGES, { id: '404', path: '/404' }]) {
  const file = p.path === '/' ? 'index.html' : p.id === '404' ? '404.html' : `${p.path.slice(1)}/index.html`
  const full = path.join(out, file)
  if (!fs.existsSync(full)) {
    console.error(`missing ${file}`)
    failed = true
    continue
  }
  const js = jsFor(full)
  const bytes = js.reduce((s, f) => s + gz(path.join(out, f)), 0)
  const css = [...fs.readFileSync(full, 'utf8').matchAll(/href="(\/assets\/[^"]+\.css)"/g)].reduce((s, m) => s + gz(path.join(out, m[1])), 0)
  rows.push({ page: p.path, js_kb_gzip: +(bytes / 1024).toFixed(1), css_kb_gzip: +(css / 1024).toFixed(1), chunks: js.length })
  if (p.path === '/' && bytes / 1024 > BUDGET_KB) failed = true
}
console.table(rows)
const home = rows.find((r) => r.page === '/')
console.log(`Home JS: ${home?.js_kb_gzip} KB gzip (budget ${BUDGET_KB} KB) → ${failed ? 'FAIL' : 'OK'}`)
process.exit(failed ? 1 : 0)
