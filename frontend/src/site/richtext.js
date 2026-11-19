import { safeHref } from './util.js'

/*
 * Client-side copy of the backend's rich-text allow-list (apps/common/sanitize.py): p, br, strong/b, em/i,
 * a[href], ul, ol, li, h3. The backend already cleans every registry richtext field on write; this runs again
 * at build (prerender) and in the browser so a snapshot that skipped that step still cannot inject markup.
 *
 * The output is rebuilt, not filtered: every tag in it is written here from the allow-list, every text run is
 * escaped, and the only attribute is an href that passed safeHref(). Unknown tags are dropped (their text kept),
 * and script/style-like elements are dropped with their content. Unclosed tags are closed at the end.
 */
const ALLOWED = new Set(['p', 'br', 'strong', 'b', 'em', 'i', 'a', 'ul', 'ol', 'li', 'h3'])
const VOID = new Set(['br'])
const DROP_WITH_CONTENT = 'script|style|iframe|object|embed|template|textarea|title|noscript|svg|math|select|xmp|noembed|noframes'
const DROP_BLOCK = new RegExp(`<(${DROP_WITH_CONTENT})\\b[\\s\\S]*?(?:<\\/\\1\\s*>|$)`, 'gi')
const TAG = /<(\/?)([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>/g
const HREF = /(?:^|\s)href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/i

const escText = (s) => s.replace(/&(?!(?:#\d{1,7}|#x[0-9a-f]{1,6}|[a-z][a-z0-9]{1,31});)/gi, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const escAttr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

function decodeEntities(s) {
  return s
    .replace(/&#x([0-9a-f]{1,6});?/gi, (_, h) => safeChar(parseInt(h, 16)))
    .replace(/&#(\d{1,7});?/g, (_, d) => safeChar(parseInt(d, 10)))
    .replace(/&(colon|tab|newline|quot|apos|lt|gt|amp);/gi, (_, n) => ({ colon: ':', tab: '\t', newline: '\n', quot: '"', apos: "'", lt: '<', gt: '>', amp: '&' })[n.toLowerCase()])
}
const safeChar = (n) => (n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : '')

export function sanitizeRichText(input) {
  if (input == null) return ''
  const html = String(input).replace(/<!--[\s\S]*?(?:-->|$)/g, '').replace(/<!\[CDATA\[[\s\S]*?(?:\]\]>|$)/g, '').replace(DROP_BLOCK, '')
  const out = []
  const open = []
  let last = 0
  for (const m of html.matchAll(TAG)) {
    out.push(escText(html.slice(last, m.index)))
    last = m.index + m[0].length
    const closing = m[1] === '/'
    const name = m[2].toLowerCase()
    if (!ALLOWED.has(name)) continue
    if (closing) {
      const at = open.lastIndexOf(name)
      if (at === -1) continue
      while (open.length > at) out.push(`</${open.pop()}>`)
      continue
    }
    if (VOID.has(name)) {
      out.push(`<${name}>`)
      continue
    }
    if (name === 'a') {
      const h = m[3].match(HREF)
      const href = h ? safeHref(decodeEntities(h[1] ?? h[2] ?? h[3] ?? '')) : null
      out.push(href ? `<a href="${escAttr(href)}" rel="noopener noreferrer">` : '<a>')
    } else {
      out.push(`<${name}>`)
    }
    open.push(name)
  }
  out.push(escText(html.slice(last)))
  while (open.length) out.push(`</${open.pop()}>`)
  return out.join('')
}

/** True when a richtext value carries markup; plain text (the backend leaves it as-is) is shown as paragraphs. */
export const hasMarkup = (value) => /<[a-z/!]/i.test(String(value || ''))
