export const visible = (rows) => (rows || []).filter((r) => r && r.is_published !== false)

/** Split CMS plain text into paragraphs on blank lines. */
export function paragraphs(text) {
  return String(text || '')
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
}

export function youtubeId(url) {
  if (!url) return null
  try {
    const u = new URL(url)
    if (u.hostname.includes('youtu.be')) return u.pathname.slice(1) || null
    if (u.pathname.startsWith('/embed/')) return u.pathname.split('/')[2] || null
    return u.searchParams.get('v')
  } catch {
    return /^[\w-]{6,}$/.test(url) ? url : null
  }
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
}

/** Nav item url can be "about", "/about", "about.html" or "/" — normalise to a route path ("/about/"). */
export function toRoute(url) {
  if (!url) return '/'
  if (/^https?:/.test(url)) return url
  const slug = url.trim().replace(/^\//, '').replace(/\.html?$/, '').replace(/\/$/, '')
  if (!slug || slug === 'home' || slug === 'index' || slug === '#') return '/'
  return `/${slug}/`
}

/**
 * Site-relative page links end in "/" (each page is <page>/index.html; Apache 301s "/about" to "/about/"),
 * so the URL served is the canonical one. Files ("/_media/x.pdf"), anchors and other schemes are untouched.
 */
export function withSlash(href) {
  if (typeof href !== 'string' || !href.startsWith('/') || href.startsWith('//')) return href
  const m = href.match(/^([^?#]*)(.*)$/)
  const path = m[1]
  if (path.endsWith('/') || /\.[a-z0-9]{2,5}$/i.test(path)) return href
  return `${path}/${m[2]}`
}

// Characters a browser ignores inside a URL scheme ("java\tscript:", leading spaces, zero-width).
const INVISIBLE = /[\u0000-\u0020\u007f-\u009f\u200b-\u200f\u2028\u2029\ufeff]/g

/**
 * Only these may become an href from snapshot data: site paths ("/…", not "//host"), "#anchor",
 * http(s):, mailto: and tel:. Anything else (javascript:, data:, vbscript:, relative "foo:bar") gives null,
 * and callers render plain text instead of a link.
 */
export function safeHref(value) {
  if (typeof value !== 'string') return null
  const href = value.trim()
  if (!href) return null
  const squashed = href.replace(INVISIBLE, '').toLowerCase()
  if (squashed.startsWith('#')) return href
  if (squashed.startsWith('/')) return squashed.startsWith('//') || squashed.startsWith('/\\') || href.includes('\\') ? null : href
  if (/^(https?:\/\/|mailto:|tel:)/.test(squashed)) return /^[a-z]/i.test(href) ? href : null
  return null
}

/** Only a hex colour ("#abc", "#aabbcc", "#aabbccdd") may become a CSS value from snapshot data. */
export function safeColor(value) {
  return typeof value === 'string' && /^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value.trim()) ? value.trim() : null
}

export function blocksFor(blocks, page) {
  const seen = new Set()
  return (blocks || []).filter((b) => {
    if (b.page && b.page !== page) return false
    const key = (b.section_title || '').trim().toLowerCase() || `id:${b.id}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

/** Drop exact-duplicate gallery rows (same image and caption), keep order. */
export function uniqueItems(items) {
  const seen = new Set()
  return (items || []).filter((it) => {
    const key = `${it.image}|${it.caption || ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}
