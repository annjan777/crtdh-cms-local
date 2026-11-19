// Snapshot-backed stand-in for the old live API client. The public site no longer calls the CMS:
// every page is pre-built from the published snapshot. Pages keep their old call shape,
// `useApi(() => fetchList('/team-members/'), [], [])`, and these functions now return a
// description that useApi() resolves against the page's snapshot data (see ./data.jsx).
export function fetchList(path, { params } = {}) {
  return { kind: 'list', name: resourceName(path), params: params || {} }
}

export function fetchOne(path) {
  return { kind: 'one', name: resourceName(path) }
}

function resourceName(path) {
  return String(path).replace(/^\/+|\/+$/g, '')
}
