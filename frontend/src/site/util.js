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

/** Nav item url can be "about", "/about", "about.html" or "/" — normalise to a route path. */
export function toRoute(url) {
  if (!url) return '/'
  if (/^https?:/.test(url)) return url
  const slug = url.trim().replace(/^\//, '').replace(/\.html?$/, '').replace(/\/$/, '')
  if (!slug || slug === 'home' || slug === 'index' || slug === '#') return '/'
  return `/${slug}`
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
