import { createContext, useContext } from 'react'

// Site components never import the router. The public app provides a router
// Link here; the admin preview can provide its own (or none: plain anchors).
const LinkContext = createContext(null)

export function LinkProvider({ component, children }) {
  return <LinkContext.Provider value={component}>{children}</LinkContext.Provider>
}

export function isExternal(href) {
  return /^(https?:)?\/\//.test(href || '') || /^(mailto|tel):/.test(href || '')
}

export default function SiteLink({ to, children, ...rest }) {
  const RouterLink = useContext(LinkContext)
  const href = to || '/'
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
