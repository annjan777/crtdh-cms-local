import { describe, expect, it } from 'vitest';
import { ApiError, CODES, mapError, networkError } from '../api/errors.js';

describe('contract §4 error mapping', () => {
  it('keeps a known server code, message, fix and extra fields', () => {
    const e = mapError(409, { code: 'CMS_STALE_VERSION', message: 'Priya Sen changed this at 10:42.', fix: 'Reload the section.', retryable: false, current_version: 7, request_id: 'r1', side_effects: 'none', changed_by: 'Priya Sen' });
    expect(e).toBeInstanceOf(ApiError);
    expect(e.code).toBe('CMS_STALE_VERSION');
    expect(e.message).toBe('Priya Sen changed this at 10:42.');
    expect(e.fix).toBe('Reload the section.');
    expect(e.currentVersion).toBe(7);
    expect(e.requestId).toBe('r1');
    expect(e.sideEffects).toBe('none');
    expect(e.details).toEqual({ changed_by: 'Priya Sen' });
  });

  it.each([
    [400, 'CMS_VALIDATION'],
    [401, 'CMS_UNAUTHENTICATED'],
    [403, 'BLOCKED'],
    [404, 'CMS_NOT_FOUND'],
    [409, 'CMS_STALE_VERSION'],
    [422, 'CMS_BUILD_GUARD'],
    [429, 'CMS_RATE_LIMITED'],
    [500, 'CMS_INTERNAL'],
    [502, 'CMS_INTERNAL'],
  ])('falls back by status %i to %s when the body has no code', (status, code) => {
    const e = mapError(status, null);
    expect(e.code).toBe(code);
    expect(e.message.length).toBeGreaterThan(0);
    expect(e.fix.length).toBeGreaterThan(0);
  });

  it('a 403 without the CMS body is reported as blocked upstream, not as a role problem', () => {
    const e = mapError(403, null);
    expect(e.code).toBe('BLOCKED');
    expect(e.message).toMatch(/not about your role/);
  });

  it('ignores codes that are not in the contract', () => {
    expect(mapError(403, { code: 'SOMETHING_ELSE' }).code).toBe('CMS_FORBIDDEN_ROLE');
  });

  it('knows the A12 codes', () => {
    expect(CODES).toContain('CMS_CSRF_FAILED');
    expect(CODES).toContain('CMS_MFA_REQUIRED');
    const csrf = mapError(403, { code: 'CMS_CSRF_FAILED' });
    expect(csrf.code).toBe('CMS_CSRF_FAILED');
    expect(csrf.retryable).toBe(true);
    expect(mapError(401, { code: 'CMS_MFA_REQUIRED' }).code).toBe('CMS_MFA_REQUIRED');
  });

  it('treats a bare 409 naming a publish as a running publish', () => {
    expect(mapError(409, { publish_id: 12 }).code).toBe('CMS_PUBLISH_RUNNING');
  });

  it('uses defaults for retryable and for overlong or missing messages', () => {
    expect(mapError(429, {}).retryable).toBe(true);
    expect(mapError(400, {}).retryable).toBe(false);
    expect(mapError(400, { code: 'CMS_VALIDATION', retryable: true }).retryable).toBe(true);
    const long = mapError(500, { code: 'CMS_INTERNAL', message: 'x'.repeat(500) });
    expect(long.message).toBe('Something went wrong on the server.');
  });

  it('keeps the field name for inline errors', () => {
    expect(mapError(400, { code: 'CMS_VALIDATION', field: 'new_password', message: 'Too short.' }).field).toBe('new_password');
  });

  it('support text carries identifiers only, never the body', () => {
    const e = mapError(500, { code: 'CMS_INTERNAL', request_id: 'abc', secret_stuff: 'x' });
    const t = JSON.parse(e.supportText('/review'));
    expect(Object.keys(t).sort()).toEqual(['at', 'code', 'request_id', 'route', 'status']);
  });

  it('network failures are retryable and promise the text is kept', () => {
    const e = networkError();
    expect(e.code).toBe('NETWORK');
    expect(e.retryable).toBe(true);
    expect(e.fix).toMatch(/kept on this computer/);
  });
});
