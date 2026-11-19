import { createContext, useContext } from 'react'
import { safeHref, withSlash } from './util.js'

// Site components never import the router. The public app provides a router
// Link here; the admin preview can provide its own (or none: plain anchors).
const LinkContext = createContext(null)

export function LinkProvider({ component, children }) {
  return <LinkContext.Provider value={component}>{children}</LinkContext.Provider>
}

export function isExternal(href) {
  return /^(https?:)?\/\//.test(href || '') || /^(mailto|tel):/.test(href || '')
}

/**
 * Every link built from snapshot data goes through here: unsafe hrefs (see safeHref) render as text,
 * and site pages get their canonical trailing slash.
 */
export default function SiteLink({ to, children, ...rest }) {
  const RouterLink = useContext(LinkContext)
  const safe = safeHref(to || '/')
  if (!safe) {
    const { className } = rest
    return <span className={className}>{children}</span>
  }
  const href = withSlash(safe)
  if (/^https?:\/\//.test(href)) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
        {children}
      </a>
    )
  }
  if (isExternal(href) || href.startsWith('#') || !RouterLink || /\.(pdf|jpe?g|png)$/i.test(href)) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  }
  return (
    <RouterLink to={href} {...rest}>
      {children}
    </RouterLink>
  )
}

/**
 * A plain <a> (files, downloads, press links) for an href from snapshot data: only safeHref() values
 * become links; anything else renders its children as text. No router, no trailing slash added.
 */
export function PlainLink({ href, children, className, ...rest }) {
  const safe = safeHref(href)
  if (!safe) return <span className={className}>{children}</span>
  return (
    <a href={safe} className={className} {...rest}>
      {children}
    </a>
  )
}
