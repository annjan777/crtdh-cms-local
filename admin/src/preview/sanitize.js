// Rich text is rendered as HTML in the canvas iframe, which is same-origin and
// runs scripts (it renders React). So every rich-text value is cleaned before
// it reaches the iframe, before the frontend lane's @site components render it.
// The backend also sanitises on write.
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = ['b', 'strong', 'i', 'em', 'a', 'ul', 'ol', 'li', 'h3', 'p', 'br'];
const SAFE_HREF = /^(https?:\/\/|mailto:|\/(?![/\\])|#|\.{0,2}\/?[\w-])/i;

let hooked = false;
function hook() {
  if (hooked) return;
  hooked = true;
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      const href = node.getAttribute('href') || '';
      if (!SAFE_HREF.test(href.trim()) || /^\s*(javascript|data|vbscript):/i.test(href)) node.removeAttribute('href');
    }
  });
}

export function sanitizeRich(html) {
  if (html === null || html === undefined) return '';
  hook();
  return DOMPurify.sanitize(String(html), { ALLOWED_TAGS, ALLOWED_ATTR: ['href'], ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false });
}

/** resource -> Set of rich-text field names, from registry pages (sections + child lists). */
export function richFieldMap(pages) {
  const map = {};
  const add = (resource, fields) => {
    for (const f of fields || []) if (f.type === 'richtext') (map[resource] ||= new Set()).add(f.name);
  };
  for (const p of pages || [])
    for (const s of p.sections || []) {
      add(s.resource, s.fields);
      for (const c of s.children || []) add(c.resource, c.fields);
    }
  return map;
}

const cleanRow = (row, names) => {
  if (!row || typeof row !== 'object') return row;
  const out = { ...row };
  for (const n of names) if (n in out) out[n] = sanitizeRich(out[n]);
  // Child lists embedded in the row (e.g. innovation images) are cleaned by their own resource entry upstream.
  return out;
};

/** Copy of preview data with every known rich-text field sanitised. */
export function sanitizePreviewData(data, map) {
  if (!data) return data;
  const singletons = { ...(data.singletons || {}) };
  const collections = { ...(data.collections || {}) };
  for (const [res, names] of Object.entries(map)) {
    if (singletons[res]) singletons[res] = cleanRow(singletons[res], names);
    if (Array.isArray(collections[res])) collections[res] = collections[res].map((r) => cleanRow(r, names));
  }
  return { ...data, singletons, collections };
}
