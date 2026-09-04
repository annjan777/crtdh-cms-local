// Shared API client for the CRTDH public frontend.
//
// Talks to the Django REST Framework backend described in API_CONTRACT.md.
// Every list endpoint returns DRF's paginated shape: {count, next, previous, results}.
// This module normalizes that away for callers that just want an array, while still
// exposing the raw response if a caller needs pagination info.

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL && import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '')) ||
  'http://localhost:8000/api/v1'

/**
 * Build a full API URL from a resource path and optional query params.
 * @param {string} path e.g. "/team-members/"
 * @param {Record<string, string|number|undefined>} [params]
 */
function buildUrl(path, params) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000'
  const fullUrl = API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')
    ? `${API_BASE_URL}${cleanPath}`
    : `${base}${API_BASE_URL}${cleanPath}`
  const url = new URL(fullUrl)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, value)
      }
    }
  }
  return url.toString()
}

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { method = 'GET', params, body, signal } = {}) {
  const url = buildUrl(path, params)
  let response
  try {
    response = await fetch(url, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (networkError) {
    // Network failures (backend down, DNS, CORS, offline, ECONNREFUSED, etc).
    // Never let this throw uncaught into a component render.
    throw new ApiError(`Network error reaching ${url}: ${networkError.message}`, 0)
  }

  if (!response.ok) {
    let detail = ''
    try {
      const data = await response.json()
      detail = data?.detail || JSON.stringify(data)
    } catch {
      // response body wasn't JSON, ignore
    }
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status)
  }

  if (response.status === 204) return null
  return response.json()
}

/**
 * Fetch a full DRF list endpoint, following `next` pagination links, and
 * return a flat array of `results`. Returns [] on any failure rather than
 * throwing, so callers can render an empty state instead of crashing.
 */
export async function fetchList(path, { params, signal } = {}) {
  try {
    let url = buildUrl(path, params)
    let results = []
    let guard = 0
    while (url && guard < 20) {
      guard += 1
      const res = await fetch(url, { signal })
      if (!res.ok) break
      const data = await res.json()
      if (Array.isArray(data)) {
        // Non-paginated array response (defensive, shouldn't normally happen)
        results = results.concat(data)
        break
      }
      results = results.concat(data.results || [])
      url = data.next || null
    }
    return results
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    console.error(`[apiClient] fetchList(${path}) failed:`, err)
    return []
  }
}

/**
 * Fetch a single-object endpoint (e.g. /site-settings/). Returns null on
 * failure instead of throwing.
 */
export async function fetchOne(path, { params, signal } = {}) {
  try {
    return await request(path, { params, signal })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    console.error(`[apiClient] fetchOne(${path}) failed:`, err)
    return null
  }
}

/**
 * POST to an endpoint. Throws ApiError on failure — callers (e.g. the
 * contact form) need to distinguish success/failure to show feedback.
 */
export async function postJSON(path, body, { signal } = {}) {
  return request(path, { method: 'POST', body, signal })
}

export { ApiError }
