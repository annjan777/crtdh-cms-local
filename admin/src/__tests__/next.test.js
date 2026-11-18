import { describe, expect, it } from 'vitest';
import { nextFromLocation, safeNext } from '../auth/next.js';

describe('OAuth next', () => {
  it.each(['/oauth/authorize/?client_id=a&state=b', '/history'])('accepts same-origin path %s', (v) => expect(safeNext(v)).toBe(v));
  it.each(['//evil.example/', '/\\evil.example', 'https://evil.example', 'javascript:alert(1)', '', null, '/a\nb'])('rejects %s', (v) => expect(safeNext(v)).toBeNull());
  it('keeps the query string', () => expect(nextFromLocation('?next=%2Foauth%2Fauthorize%2F%3Fa%3D1%26b%3D2')).toBe('/oauth/authorize/?a=1&b=2'));
});
