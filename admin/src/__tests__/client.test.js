import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, setTransport } from '../api/client.js';

function res(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('API client: session + in-memory CSRF (addendum A12)', () => {
  afterEach(() => setTransport(null));

  it('fetches the token from the csrf body and sends it as X-CSRFToken, never via cookie', async () => {
    const calls = [];
    setTransport(async (url, init) => {
      calls.push([url, init]);
      if (url.endsWith('/auth/csrf/')) return res(200, { csrfToken: 'tok-1' });
      return res(200, { ok: true });
    });
    await api.post('/cms/discard/', { item_ids: [] });
    const [url, init] = calls.at(-1);
    expect(url).toBe('/api/v1/cms/discard/');
    expect(init.headers['X-CSRFToken']).toBe('tok-1');
    expect(init.credentials).toBe('include');
    expect(document.cookie).not.toContain('csrftoken');
  });

  it('switches to the fresh token a login/MFA response returns', async () => {
    const sent = [];
    setTransport(async (url, init) => {
      if (url.endsWith('/auth/csrf/')) return res(200, { csrfToken: 'old' });
      sent.push(init.headers['X-CSRFToken']);
      if (url.endsWith('/auth/mfa/')) return res(200, { id: 1, username: 'priya', csrfToken: 'new' });
      return res(200, {});
    });
    await api.post('/auth/mfa/', { code: '123456' });
    await api.post('/cms/publish/', {});
    expect(sent).toEqual(['old', 'new']);
  });

  it('on CMS_CSRF_FAILED refetches the token and retries once', async () => {
    let csrfFetches = 0;
    let attempts = 0;
    setTransport(async (url, init) => {
      if (url.endsWith('/auth/csrf/')) {
        csrfFetches += 1;
        return res(200, { csrfToken: `t${csrfFetches}` });
      }
      attempts += 1;
      if (init.headers['X-CSRFToken'] === 't1') return res(403, { code: 'CMS_CSRF_FAILED', message: 'expired' });
      return res(200, { done: true });
    });
    await expect(api.post('/cms/publish/', {})).resolves.toEqual({ done: true });
    expect(csrfFetches).toBe(2);
    expect(attempts).toBe(2);
  });

  it('a 401 outside the sign-in endpoints announces an expired session', async () => {
    const spy = vi.fn();
    window.addEventListener('crtdh:session-expired', spy);
    setTransport(async () => res(401, { code: 'CMS_UNAUTHENTICATED' }));
    await expect(api.get('/cms/changes/')).rejects.toMatchObject({ code: 'CMS_UNAUTHENTICATED' });
    expect(spy).toHaveBeenCalledTimes(1);
    await expect(api.get('/auth/me/')).rejects.toMatchObject({ code: 'CMS_UNAUTHENTICATED' });
    expect(spy).toHaveBeenCalledTimes(1);
    window.removeEventListener('crtdh:session-expired', spy);
  });

  it('a failed fetch becomes a NETWORK error', async () => {
    setTransport(async () => {
      throw new TypeError('Failed to fetch');
    });
    await expect(api.get('/cms/pages/')).rejects.toMatchObject({ code: 'NETWORK' });
  });

  it('does not keep anything token-like in localStorage', async () => {
    setTransport(async (url) => (url.endsWith('/auth/csrf/') ? res(200, { csrfToken: 'x' }) : res(200, {})));
    await api.post('/auth/logout/', {});
    expect(Object.keys(localStorage).filter((k) => /token|csrf|jwt/i.test(k))).toEqual([]);
  });
});
