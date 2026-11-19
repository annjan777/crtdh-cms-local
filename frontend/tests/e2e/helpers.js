import fs from 'node:fs'

export const snapshot = JSON.parse(fs.readFileSync(process.env.SNAPSHOT_PATH || 'snapshot.json', 'utf8'))
export const ROUTES = ['/', '/about/', '/team/', '/innovations/', '/facilities/', '/services/', '/product/', '/enterprises/', '/social-impact/', '/covid-19/', '/media/', '/contact/']
export const visible = (rows) => (rows || []).filter((r) => r.is_published !== false)

/** Requests a static page may make: its own origin; the embedded YouTube players (privacy-enhanced youtube-nocookie) and the map embed are third-party media. */
export function isAllowedRequest(url, base) {
  const u = new URL(url)
  if (u.origin === new URL(base).origin) return !u.pathname.startsWith('/api/')
  return ['i.ytimg.com', 'www.youtube-nocookie.com', 'www.google.com', 'maps.google.com', 'maps.gstatic.com', 'fonts.gstatic.com'].includes(u.hostname)
}

/** Assert every string appears in the text, in this order. */
export function expectInOrder(expect, text, items, label) {
  let at = -1
  const norm = (s) => String(s).replace(/\s+/g, ' ').trim()
  const hay = norm(text)
  for (const item of items) {
    const i = hay.indexOf(norm(item), at + 1)
    expect(i, `${label}: "${item}" missing or out of order`).toBeGreaterThan(at)
    at = i
  }
}
