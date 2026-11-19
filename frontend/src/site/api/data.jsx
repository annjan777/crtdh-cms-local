import { createContext, useContext } from 'react'

// Snapshot-shaped data ({ singletons, collections, media }) for the page being rendered.
// The public build passes each page its loader data; the admin canvas passes the preview data.
const PageDataContext = createContext(null)

export function PageDataProvider({ data, children }) {
  const parent = useContext(PageDataContext)
  // Pages also see the layout's data (site settings, navigation) when they don't carry their own.
  const merged = parent && data ? {
    ...parent,
    ...data,
    singletons: { ...(parent.singletons || {}), ...(data.singletons || {}) },
    collections: { ...(parent.collections || {}), ...(data.collections || {}) },
    media: { ...(parent.media || {}), ...(data.media || {}) },
  } : data || parent
  return <PageDataContext.Provider value={merged}>{children}</PageDataContext.Provider>
}

export function usePageData() {
  return useContext(PageDataContext)
}

/** Resolve a fetchList/fetchOne description against snapshot data. */
export function resolve(data, req) {
  if (!req || !data) return undefined
  if (req.kind === 'one') return data.singletons?.[req.name] ?? undefined
  let rows = (data.collections?.[req.name] || []).filter((r) => r && r.is_published !== false)
  for (const [key, value] of Object.entries(req.params || {})) {
    if (value !== undefined && value !== null && value !== '') rows = rows.filter((r) => String(r[key]) === String(value))
  }
  return rows
}
