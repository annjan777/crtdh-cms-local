import { afterEach, describe, expect, it } from 'vitest';
import { richFieldMap, sanitizePreviewData, sanitizeRich } from '../preview/sanitize.js';
import { clearDraft, clearUserDrafts, readDraft, setDraftOwner, writeDraft } from '../editor/drafts.js';
import { isValidUrl } from '../editor/validate.js';
import { setTransport } from '../api/client.js';
import { messages } from '../api/cms.js';

describe('rich text sanitising for the canvas', () => {
  it('keeps the allowed marks and drops everything else', () => {
    const out = sanitizeRich('<p>Hi <strong>b</strong> <em>i</em><script>alert(1)</script><img src=x onerror=alert(1)><h3>T</h3><ul><li>x</li></ul><h1>big</h1><span style="color:red">s</span></p>');
    expect(out).toContain('<p>Hi <strong>b</strong> <em>i</em>');
    expect(out).toContain('<h3>T</h3><ul><li>x</li></ul>bigs');
    expect(out).not.toMatch(/script|img|onerror|<h1|<span|style/);
  });
  it('allows only http(s), mailto and relative links', () => {
    expect(sanitizeRich('<a href="https://iitkgp.ac.in">a</a>')).toBe('<a href="https://iitkgp.ac.in">a</a>');
    expect(sanitizeRich('<a href="/media">a</a>')).toBe('<a href="/media">a</a>');
    expect(sanitizeRich('<a href="mailto:x@y.in">a</a>')).toBe('<a href="mailto:x@y.in">a</a>');
    expect(sanitizeRich('<a href="javascript:alert(1)">a</a>')).toBe('<a>a</a>');
    expect(sanitizeRich('<a href="//evil.example">a</a>')).toBe('<a>a</a>');
    expect(sanitizeRich('<a href="data:text/html,x">a</a>')).toBe('<a>a</a>');
    expect(sanitizeRich('<a href="/x" onclick="x()" target="_blank">a</a>')).toBe('<a href="/x">a</a>');
  });
  it('cleans only rich-text fields named by the registry', () => {
    const map = richFieldMap([{ sections: [{ resource: 'home-page', fields: [{ name: 'body', type: 'richtext' }, { name: 'title', type: 'text' }] }, { resource: 'innovations', fields: [], children: [{ resource: 'x', fields: [{ name: 'note', type: 'richtext' }] }] }] }]);
    expect([...map['home-page']]).toEqual(['body']);
    expect([...map.x]).toEqual(['note']);
    const data = { singletons: { 'home-page': { body: '<p>ok</p><script>x</script>', title: 'a < b <b>' } }, collections: { x: [{ note: '<img src=x onerror=1>t' }] } };
    const clean = sanitizePreviewData(data, map);
    expect(clean.singletons['home-page']).toEqual({ body: '<p>ok</p>', title: 'a < b <b>' });
    expect(clean.collections.x[0].note).toBe('t');
    expect(data.singletons['home-page'].body).toContain('script');
  });
});

describe('drafts are per user', () => {
  afterEach(() => localStorage.clear());
  it('one user never reads another user’s draft; sign-out clears only theirs', () => {
    setDraftOwner(1);
    writeDraft('home-page:1', { body: 'priya' }, 3);
    setDraftOwner(2);
    expect(readDraft('home-page:1')).toBeNull();
    writeDraft('home-page:1', { body: 'ravi' }, 3);
    clearUserDrafts(1);
    expect(readDraft('home-page:1').values.body).toBe('ravi');
    setDraftOwner(1);
    expect(readDraft('home-page:1')).toBeNull();
    setDraftOwner(null);
    writeDraft('a:1', { x: 1 }, 1);
    expect(Object.keys(localStorage)).toEqual(['crtdh-draft:2:home-page:1']);
    clearDraft('a:1');
  });
});

describe('url fields', () => {
  it('reject protocol-relative addresses', () => {
    expect(isValidUrl('/innovations')).toBe(true);
    expect(isValidUrl('//evil.example')).toBe(false);
    expect(isValidUrl('/\\evil.example')).toBe(false);
  });
});

describe('messages list', () => {
  afterEach(() => setTransport(null));
  it('follows next across pages', async () => {
    const seen = [];
    setTransport(async (url) => {
      seen.push(url);
      const body = url.includes('page=2')
        ? { results: [{ id: 2 }], next: null }
        : { results: [{ id: 1 }], next: 'http://localhost:3000/api/v1/contact-messages/?page=2' };
      return new Response(JSON.stringify(body), { status: 200 });
    });
    expect(await messages.list()).toEqual([{ id: 1 }, { id: 2 }]);
    expect(seen).toEqual(['/api/v1/contact-messages/', '/api/v1/contact-messages/?page=2']);
  });
});
