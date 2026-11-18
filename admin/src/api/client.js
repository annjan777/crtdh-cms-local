// HTTP client for the CMS API (contract §3). Session cookie + CSRF only:
// no tokens are ever read from or written to localStorage.
//
// With VITE_USE_MOCK=1 the same calls go to an in-browser fake of the API
// (src/mock/server.js) so the admin can be built and tested before the
// backend lanes land. The fake is never bundled when the flag is off.

import { mapError, networkError } from './errors.js';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1';

let transport = null;
async function getTransport() {
  if (transport) return transport;
  if (USE_MOCK) {
    const { mockFetch } = await import('../mock/server.js');
    transport = mockFetch;
  } else {
    transport = (url, init) => fetch(url, init);
  }
  return transport;
}

// For unit tests.
export function setTransport(fn) {
  transport = fn;
  csrfReady = null;
  csrfToken = null;
}

// Addendum A12: the CSRF cookie is HttpOnly. The token comes in the body of
// GET /auth/csrf/ and of the login/MFA/password responses, and lives only in
// memory (never localStorage).
let csrfToken = null;
let csrfReady = null;
export function ensureCsrf(force = false) {
  if (force || !csrfReady || !csrfToken) {
    csrfReady = rawRequest('GET', '/auth/csrf/').catch((e) => {
      csrfReady = null;
      throw e;
    });
  }
  return csrfReady;
}

const SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);
const AUTH_PATHS = ['/auth/login/', '/auth/mfa/', '/auth/me/', '/auth/csrf/', '/auth/mfa/enrol/'];

async function rawRequest(method, path, { body, form } = {}) {
  const send = await getTransport();
  const headers = { Accept: 'application/json' };
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  if (!SAFE.has(method)) {
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
  }
  let res;
  try {
    res = await send(`${API_BASE}${path}`, { method, headers, body: payload, credentials: 'include' });
  } catch {
    throw networkError();
  }
  if (res.status === 204) return null;
  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (data && typeof data.csrfToken === 'string') csrfToken = data.csrfToken;
  if (!res.ok) {
    const err = mapError(res.status, data);
    if ((err.code === 'CMS_UNAUTHENTICATED' || err.code === 'CMS_MFA_REQUIRED') && !AUTH_PATHS.some((p) => path.startsWith(p)) && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('crtdh:session-expired'));
    }
    throw err;
  }
  return data;
}

export async function request(method, path, opts = {}) {
  if (!SAFE.has(method)) await ensureCsrf();
  try {
    return await rawRequest(method, path, opts);
  } catch (err) {
    // A rotated or missing CSRF token: fetch a fresh one and retry once.
    if (err.code === 'CMS_CSRF_FAILED' || (err.status === 403 && err.details?.detail?.toLowerCase?.().includes('csrf'))) {
      await ensureCsrf(true);
      return rawRequest(method, path, opts);
    }
    throw err;
  }
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, body) => request('POST', p, { body }),
  patch: (p, body) => request('PATCH', p, { body }),
  patchForm: (p, form) => request('PATCH', p, { form }),
  del: (p) => request('DELETE', p),
};
