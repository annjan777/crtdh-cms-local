import { createContext, useContext } from 'react'
import SiteLink from './link.jsx'
import { withSlash } from './util.js'

// The old design was written against react-router-dom. Site components must not import the router
// (the admin canvas renders them without one), so these stand in for Link, NavLink and useLocation.
const PathContext = createContext('/')

export function CurrentPathProvider({ path, children }) {
  return <PathContext.Provider value={path || '/'}>{children}</PathContext.Provider>
}

export function useLocation() {
  return { pathname: useContext(PathContext), hash: '', search: '' }
}

const norm = (p) => withSlash(String(p || '/').split(/[?#]/)[0]) || '/'

export function isActive(current, to, end) {
  const a = norm(current)
  const b = norm(to)
  if (b === '/' || end) return a === b
  return a === b || a.startsWith(b)
}

export function Link({ to, ...rest }) {
  return <SiteLink to={to} {...rest} />
}

export function NavLink({ to, end, className, children, ...rest }) {
  const active = isActive(useContext(PathContext), to, end)
  const cls = [typeof className === 'function' ? className({ isActive: active }) : className, active ? 'active' : '']
    .filter(Boolean)
    .join(' ')
  return (
    <SiteLink to={to} className={cls || undefined} aria-current={active ? 'page' : undefined} {...rest}>
      {typeof children === 'function' ? children({ isActive: active }) : children}
    </SiteLink>
  )
}
