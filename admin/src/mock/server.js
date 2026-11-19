// In-browser fake of the CMS API (contract §3/§4), used when VITE_USE_MOCK=1.
// It is a test double, not a backend: state lives in sessionStorage so a
// reload keeps it, and a new browser context starts from the seed.
//
// Local test values only: every seeded user signs in with the password
// "local-test-pass" and the authenticator code "246810".

import seed from './seed-snapshot.json';
import dims from './media-dims.json';
import { REGISTRY, SINGLETON_RESOURCES } from './registry.js';

const DB_KEY = 'crtdh-mock-db';
const SESSION_KEY = 'crtdh-mock-session';
export const TEST_PASSWORD = 'local-test-pass';
export const TEST_CODE = '246810';
const RECOVERY = ['4kq7-mx2p', '9tz3-wd8h', 'r6vn-2cfa', 'p8ye-k3us', 'h2bw-7jqn', 'm5xs-9edr', 'c3ua-6gkt', 'w7fd-4npz'];

const clone = (x) => JSON.parse(JSON.stringify(x));
const SEED_MESSAGES = [
  { id: 41, name: 'Anita Roy', email: 'anita.roy@example.test', phone: '+91 98300 00000', message: 'Hello, we run a small diagnostics start-up in Durgapur and would like to know about membership &amp; access to the PCR facility. Could someone call me?', created_at: '2026-11-18T09:12:00Z' },
  { id: 40, name: 'Dr. S. Mehta', email: 'smehta@example.test', phone: '', message: 'Is the eye camp on 2 December open to walk-ins? We&#x27;d like to bring 20 people from our village.', created_at: '2026-11-16T15:40:00Z' },
  { id: 39, name: 'Test &lt;script&gt;', email: 'probe@example.test', phone: '', message: '&lt;img src=x onerror=alert(1)&gt; shown as text, never run', created_at: '2026-11-12T11:05:00Z' },
];
const nowIso = () => new Date().toISOString();
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- seed --

// Previews read uploaded files through the API (session required), never from
// /media/ (the public Media & Gallery page) or /_media/ (published, hashed; A13).
export const MEDIA_PREFIX = '/api/v1/media/';
function localMedia(url) {
  return typeof url === 'string' ? url.replace(/^https?:\/\/localhost:8000\/media\//, MEDIA_PREFIX) : url;
}

const CHILD_ARRAYS = { innovations: ['images'], products: ['images', 'partners'], 'media-events': ['images'], 'image-grid-blocks': ['items'] };

function imageFields() {
  // resource -> [{name, alt_field}]
  const out = {};
  const visit = (resource, fields) => {
    for (const f of fields) if (f.type === 'image') (out[resource] ||= []).push(f);
  };
  for (const p of REGISTRY.pages)
    for (const s of p.sections) {
      visit(s.resource, s.fields);
      for (const c of s.children || []) visit(c.resource, c.fields);
    }
  return out;
}
const IMAGE_FIELDS = imageFields();

function prepRow(resource, row) {
  const r = {};
  for (const [k, v] of Object.entries(row)) {
    if ((CHILD_ARRAYS[resource] || []).includes(k)) continue;
    r[k] = localMedia(v);
  }
  r.version = 1;
  if (!SINGLETON_RESOURCES.includes(resource) && !('is_published' in r)) r.is_published = true;
  for (const f of IMAGE_FIELDS[resource] || []) if (!(f.alt_field in r)) r[f.alt_field] = '';
  if (resource === 'hero-slides') r.alt_text = r.alt_text || '';
  return r;
}

const USERS = [
  { id: 1, username: 'priya', name: 'Priya Sen', email: 'priya@example.test', roles: ['editor', 'publisher'], mfa_enrolled: true, is_active: true, last_login: '2026-11-19T04:12:00Z' },
  { id: 2, username: 'ravi', name: 'Ravi Kumar', email: 'ravi@example.test', roles: ['editor'], mfa_enrolled: true, is_active: true, last_login: '2026-11-18T10:40:00Z' },
  { id: 3, username: 'sita', name: 'Sita Das', email: 'sita@example.test', roles: ['editor', 'publisher', 'admin'], mfa_enrolled: true, is_active: true, last_login: '2026-11-17T08:05:00Z' },
  { id: 4, username: 'arjun', name: 'Arjun Paul', email: 'arjun@example.test', roles: ['editor'], mfa_enrolled: false, is_active: true, last_login: null },
  { id: 6, username: 'meera', name: 'Meera Iyer', email: 'meera@example.test', roles: ['editor'], mfa_enrolled: true, must_change_password: true, is_active: true, last_login: null },
  { id: 5, username: 'mohan', name: 'Mohan Roy', email: 'mohan@example.test', roles: [], mfa_enrolled: true, is_active: false, last_login: '2026-06-02T09:00:00Z' },
];

function buildSeed() {
  const rows = {};
  for (const [res, row] of Object.entries(seed.singletons)) rows[res] = { [row.id]: prepRow(res, row) };
  for (const [res, list] of Object.entries(seed.collections)) {
    rows[res] = {};
    for (const row of list) rows[res][row.id] = prepRow(res, row);
  }
  const published = clone(rows);
  const db = {
    users: clone(USERS),
    // Live Claude connections by user id (GET /cms/claude-access/; revoke clears them).
    claude: { 1: [{ client: 'Claude', connected_at: '2026-11-18T09:15:00Z' }], 2: [{ client: 'Claude', connected_at: '2026-11-17T14:02:00Z' }] },
    rows,
    published,
    meta: {},
    audit: [],
    snapshots: [],
    publishes: {},
    nextId: 5000,
    nextPublish: 41,
    failedLogins: {},
    flags: { agentOffline: false, failNext: null, agentLastSeen: '2026-11-19T03:40:00Z', expired: false },
    reviewRequest: null,
  };
  // Three earlier publishes for History.
  const older = clone(published);
  const news = Object.values(older['news-items'])[0];
  if (news) news.text = 'CRTDH team visits Rural Healthcare Foundation clinics';
  db.snapshots = [
    { id: 40, snapshot_id: '2026-11-18T12:10:00Z-9c1e4b', published_at: '2026-11-18T12:10:00Z', published_by: 'Priya Sen', note: 'Team page photos', rows: clone(published) },
    { id: 39, snapshot_id: '2026-11-12T05:35:00Z-2a7f10', published_at: '2026-11-12T05:35:00Z', published_by: 'Priya Sen', note: 'News ticker update', rows: older },
    { id: 38, snapshot_id: '2026-11-04T10:50:00Z-77b3d2', published_at: '2026-11-04T10:50:00Z', published_by: 'Sita Das', note: 'First published snapshot', rows: clone(older) },
  ];
  // Two unpublished drafts so the review screen has work on first open:
  // one written by Claude (MCP) on Priya's behalf, one by Ravi in the admin.
  const member = Object.values(rows['team-members']).find((m) => m.name.includes('Chakraborty')) || Object.values(rows['team-members'])[0];
  const before = member.designation;
  member.designation = 'Principal Investigator, CRTDH';
  member.version = 2;
  const memberAt = '2026-11-19T03:52:00Z';
  db.meta[`team-members:${member.id}`] = { author: 'Priya Sen', channel: 'claude', session_id: 'mcp-7f3a21', at: memberAt };
  db.audit.push({ item_id: `team.members.team-members:${member.id}`, at: memberAt, author: 'Priya Sen', channel: 'claude', session_id: 'mcp-7f3a21', action: 'changed', fields: [{ name: 'designation', before, after: member.designation }] });
  const newsId = 4001;
  rows['news-items'][newsId] = { id: newsId, text: 'Health camp at Salboni on 28 November — free eye and blood-sugar screening', link_url: '/media', order: 6, is_published: true, version: 1 };
  db.meta[`news-items:${newsId}`] = { author: 'Ravi Kumar', channel: 'admin', at: '2026-11-19T04:30:00Z' };
  db.audit.push({ item_id: `home.news.news-items:${newsId}`, at: '2026-11-19T04:30:00Z', author: 'Ravi Kumar', channel: 'admin', action: 'added', fields: [] });
  return db;
}

let db = null;
function load() {
  if (db) return db;
  try {
    const raw = sessionStorage.getItem(DB_KEY);
    db = raw ? JSON.parse(raw) : buildSeed();
  } catch {
    db = buildSeed();
  }
  return db;
}
function save() {
  try {
    sessionStorage.setItem(DB_KEY, JSON.stringify(db));
  } catch {
    /* quota: keep in memory */
  }
}

function session() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
  } catch {
    return null;
  }
}
function setSession(s) {
  if (s) sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
  else sessionStorage.removeItem(SESSION_KEY);
}
// A12: the real CSRF cookie is HttpOnly, so the page can't read it. The mock
// keeps "the server's" token out of reach of the client code (sessionStorage
// key the client never touches) and hands it over only in response bodies.
const CSRF_KEY = 'crtdh-mock-csrf';
function setCsrfCookie() {
  const token = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  sessionStorage.setItem(CSRF_KEY, token);
  return token;
}
function csrfCookie() {
  return sessionStorage.getItem(CSRF_KEY);
}

// ------------------------------------------------------------ registry --

const PAGES = REGISTRY.pages;

function matchesFilter(section, row) {
  return !section.filter || Object.entries(section.filter).every(([k, v]) => row[k] === v);
}

function locate(resource, row) {
  // -> {page, section, child?}
  for (const page of PAGES)
    for (const section of page.sections) {
      if (section.kind === 'collection' && section.resource === resource && matchesFilter(section, row)) return { page, section };
      for (const child of section.children || [])
        if (child.resource === resource) {
          const parent = db.rows[section.resource]?.[row[child.parent_field]] || db.published[section.resource]?.[row[child.parent_field]];
          if (!parent || matchesFilter(section, parent)) return { page, section, child, parent };
        }
    }
  return null;
}

function sectionForField(resource, field) {
  for (const page of PAGES)
    for (const section of page.sections)
      if (section.kind === 'singleton' && section.resource === resource && section.fields.some((f) => f.name === field || f.alt_field === field || f.position_field === field))
        return { page, section };
  return null;
}

function fieldDef(resource, name) {
  for (const page of PAGES)
    for (const section of page.sections) {
      const lists = [section.resource === resource ? section.fields : [], ...(section.children || []).filter((c) => c.resource === resource).map((c) => c.fields)];
      for (const fields of lists)
        for (const f of fields) {
          if (f.name === name) return f;
          if (f.alt_field === name) return { name, label: `${f.label} description`, type: 'text' };
          if (f.position_field === name) return { name, label: `${f.label} focus point`, type: 'text' };
        }
    }
  if (name === 'is_published') return { name, label: 'Shown on site', type: 'boolean' };
  if (name === 'order') return { name, label: 'Position', type: 'number' };
  return { name, label: name, type: 'text' };
}

function itemLabel(def, row, fallbackNoun) {
  const parts = (def.item_label || []).map((n) => row?.[n]).filter((x) => x && String(x).trim());
  const text = parts.join(' ').replace(/<[^>]+>/g, '').trim();
  if (text) return text.length > 70 ? `${text.slice(0, 67)}…` : text;
  return `${fallbackNoun} ${row?.id ?? ''}`.trim();
}

function mediaInfo(url) {
  if (!url) return null;
  const known = db.media?.[url];
  if (known) return known;
  const d = dims[url] || dims[String(url).replace(MEDIA_PREFIX, '/media/')];
  return d ? { width: d[0], height: d[1], name: url.split('/').pop() } : null;
}

// ----------------------------------------------------------- responses --

function json(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}
const rid = () => Math.random().toString(16).slice(2, 10);
function fail(status, code, message, fix, extra = {}) {
  return json(status, { code, message, fix, retryable: ['CMS_RATE_LIMITED', 'CMS_INTERNAL', 'CMS_PUBLISH_RUNNING'].includes(code), side_effects: 'none', field: null, current_version: null, request_id: rid(), ...extra });
}

function me(user) {
  return { id: user.id, username: user.username, name: user.name, email: user.email, roles: user.is_active ? user.roles : [], mfa_enrolled: user.mfa_enrolled, must_change_password: !!user.must_change_password };
}
const ROLE_ORDER = ['editor', 'publisher', 'admin'];
const rolesUpTo = (role) => ROLE_ORDER.slice(0, ROLE_ORDER.indexOf(role) + 1);
const can = (user, ...roles) => user.roles.some((r) => r === 'admin' || roles.includes(r));

const timeOf = (iso) => new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' });

// --------------------------------------------------------------- diff --

const SKIP = new Set(['version', 'id', 'category_name']);

function diffFields(resource, before, after) {
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
  const out = [];
  for (const k of keys) {
    if (SKIP.has(k)) continue;
    const a = before?.[k] ?? '';
    const b = after?.[k] ?? '';
    if (JSON.stringify(a) !== JSON.stringify(b)) out.push({ name: k, label: fieldDef(resource, k).label, before: a, after: b });
  }
  return out;
}

function computeChanges() {
  const pages = new Map();
  const push = (page, change) => {
    if (!pages.has(page.id)) pages.set(page.id, { page: page.id, title: page.title, changes: [] });
    pages.get(page.id).changes.push(change);
  };
  const resources = new Set([...Object.keys(db.rows), ...Object.keys(db.published)]);
  for (const resource of resources) {
    const cur = db.rows[resource] || {};
    const pub = db.published[resource] || {};
    const pks = new Set([...Object.keys(cur), ...Object.keys(pub)]);
    for (const pk of pks) {
      const a = pub[pk];
      const b = cur[pk];
      const meta = db.meta[`${resource}:${pk}`] || { author: 'Unknown', channel: 'admin', at: null };
      if (SINGLETON_RESOURCES.includes(resource)) {
        const bySection = new Map();
        for (const f of diffFields(resource, a, b)) {
          const loc = sectionForField(resource, f.name);
          if (!loc) continue;
          if (!bySection.has(loc.section.id)) bySection.set(loc.section.id, { loc, fields: [] });
          bySection.get(loc.section.id).fields.push(f);
        }
        for (const { loc, fields } of bySection.values())
          push(loc.page, { item_id: `${loc.section.id}.${resource}:${pk}`, resource, pk: Number(pk), label: loc.section.label, section: loc.section.label, kind: 'changed', fields, ...meta });
        continue;
      }
      const row = b || a;
      const loc = locate(resource, row);
      if (!loc) continue;
      const def = loc.child || loc.section;
      const noun = loc.child ? def.add_label : loc.section.item_noun || loc.section.add_label || 'item';
      let label = itemLabel(def, row, noun.charAt(0).toUpperCase() + noun.slice(1));
      if (loc.child && loc.parent) label = `${loc.child.label.replace(/s$/, '')} in “${itemLabel(loc.section, loc.parent, 'item')}”`;
      const base = { item_id: `${loc.section.id}.${resource}:${pk}`, resource, pk: Number(pk), label, section: loc.section.label, ...meta };
      if (!a) push(loc.page, { ...base, kind: 'added', fields: diffFields(resource, {}, b).filter((f) => f.after !== '' && f.name !== 'order' && f.name !== 'is_published') });
      else if (!b) push(loc.page, { ...base, kind: 'removed', fields: [] });
      else {
        const fields = diffFields(resource, a, b);
        if (!fields.length) continue;
        const hidden = a.is_published !== false && b.is_published === false;
        push(loc.page, { ...base, kind: hidden ? 'hidden' : 'changed', fields: fields.filter((f) => !(hidden && f.name === 'is_published')) });
      }
    }
  }
  const order = PAGES.map((p) => p.id);
  const list = [...pages.values()].sort((x, y) => order.indexOf(x.page) - order.indexOf(y.page));
  return { count: list.reduce((n, p) => n + p.changes.length, 0), pages: list, review_request: db.reviewRequest };
}

function audit(user, channel, itemId, action, fields) {
  db.audit.push({ item_id: itemId, at: nowIso(), author: user.name, channel, action, fields });
}

function itemIdFor(resource, row, changedFields) {
  if (SINGLETON_RESOURCES.includes(resource)) {
    const loc = sectionForField(resource, changedFields?.[0] || '');
    return `${loc ? loc.section.id : resource}.${resource}:${row.id}`;
  }
  const loc = locate(resource, row);
  return `${loc ? loc.section.id : resource}.${resource}:${row.id}`;
}

// ------------------------------------------------------------ content --

function sortRows(list) {
  return list.sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || a.id - b.id);
}

function itemOut(resource, row, def, sectionId) {
  const values = { ...row };
  delete values.version;
  const media = {};
  for (const f of def.fields) if (f.type === 'image') media[f.name] = mediaInfo(row[f.name]);
  return { item_id: `${sectionId}.${resource}:${row.id}`, pk: row.id, version: row.version, values, media };
}

function pageOut(page) {
  return {
    id: page.id,
    path: page.path,
    title: page.title,
    sections: page.sections.map((s) => {
      const out = { ...s };
      if (s.kind === 'singleton') {
        const row = Object.values(db.rows[s.resource] || {})[0];
        out.items = row ? [itemOut(s.resource, row, s, s.id)] : [];
      } else {
        const rows = sortRows(Object.values(db.rows[s.resource] || {}).filter((r) => matchesFilter(s, r)));
        out.items = rows.map((r) => {
          const item = itemOut(s.resource, r, s, s.id);
          if (s.children) {
            item.children = {};
            for (const c of s.children)
              item.children[c.resource] = sortRows(Object.values(db.rows[c.resource] || {}).filter((x) => x[c.parent_field] === r.id)).map((x) => itemOut(c.resource, x, c, s.id));
          }
          return item;
        });
      }
      return out;
    }),
  };
}

function previewOut() {
  const visible = (r) => r.is_published !== false;
  const collections = {};
  for (const [res, map] of Object.entries(db.rows)) {
    if (SINGLETON_RESOURCES.includes(res)) continue;
    collections[res] = sortRows(Object.values(map).filter(visible).map((r) => ({ ...r })));
  }
  const kids = (res, field, id) => (collections[res] || []).filter((x) => x[field] === id);
  for (const r of collections.innovations || []) r.images = kids('innovation-images', 'innovation', r.id);
  for (const r of collections.products || []) {
    r.images = kids('product-images', 'product', r.id);
    r.partners = kids('product-partners', 'product', r.id);
  }
  for (const r of collections['media-events'] || []) r.images = kids('media-event-images', 'event', r.id);
  for (const r of collections['image-grid-blocks'] || []) r.items = kids('image-grid-items', 'block', r.id);
  const cats = Object.fromEntries((collections['team-categories'] || []).map((c) => [c.id, c.name]));
  for (const r of collections['team-members'] || []) r.category_name = cats[r.category] || '';
  const singletons = {};
  for (const res of SINGLETON_RESOURCES) singletons[res] = { ...Object.values(db.rows[res] || {})[0] };
  return { schema_version: 1, snapshot_id: 'preview', published_at: null, singletons, collections };
}

function validate(resource, values, row) {
  for (const [name, v] of Object.entries(values)) {
    const f = fieldDef(resource, name);
    if (f.required && (v === '' || v === null || v === undefined))
      return fail(400, 'CMS_VALIDATION', `${f.label} can’t be empty.`, `Enter ${f.label.toLowerCase()}.`, { field: name });
    if (f.max && typeof v === 'string' && v.replace(/<[^>]+>/g, '').length > f.max)
      return fail(400, 'CMS_VALIDATION', `${f.label} is longer than ${f.max} characters.`, 'Shorten it.', { field: name });
    if (f.type === 'url' && v && !/^(\/|https?:\/\/|mailto:)/.test(v))
      return fail(400, 'CMS_VALIDATION', `${f.label} must start with / or https://.`, 'Use a page path like /innovations or a full web address.', { field: name });
  }
  void row;
  return null;
}

async function readImage(file) {
  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;
  const scale = Math.min(1, 1000 / width);
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return { width, height, url: canvas.toDataURL('image/jpeg', 0.72) };
}

async function patchRow(user, resource, pk, body) {
  const map = db.rows[resource];
  const row = map?.[pk];
  if (!row) return fail(404, 'CMS_NOT_FOUND', `${resource}:${pk} no longer exists.`, 'Reload the page.');
  let values = {};
  let expected;
  if (body instanceof FormData) {
    for (const [k, v] of body.entries()) values[k] = v;
    expected = Number(values.expected_version);
  } else {
    values = { ...body };
    expected = values.expected_version;
  }
  delete values.expected_version;
  const itemId = itemIdFor(resource, row, Object.keys(values));
  if (expected !== row.version) {
    const last = [...db.audit].reverse().find((a) => a.item_id.endsWith(`.${resource}:${pk}`)) || { author: 'someone', at: nowIso() };
    return fail(409, 'CMS_STALE_VERSION', `${itemId} changed since you read it (you sent v${expected}, current v${row.version}, edited by ${last.author.split(' ')[0].toLowerCase()} at ${timeOf(last.at)}).`, 'Reload the section and reapply your change.', {
      current_version: row.version,
      edited_by: last.author,
      edited_at: last.at,
    });
  }
  // Files: size rule and alt rule (contract §2 image fields).
  for (const [name, v] of Object.entries(values)) {
    if (typeof File !== 'undefined' && v instanceof File) {
      const f = fieldDef(resource, name);
      let img;
      try {
        img = await readImage(v);
      } catch {
        return fail(400, 'CMS_VALIDATION', 'This file isn’t a photo the site can use.', 'Choose a JPEG, PNG or WebP photo.', { field: name });
      }
      if (f.min_width && img.width < f.min_width)
        return fail(400, 'CMS_IMAGE_TOO_SMALL', `This photo is ${img.width} px wide. ${f.label}s here need at least ${f.min_width} px.`, 'Choose a larger photo. The shot list says which photos to take.', { field: name, width: img.width, min_width: f.min_width });
      const altName = f.alt_field;
      const alt = values[altName] ?? row[altName];
      if (altName && !String(alt || '').trim()) return fail(400, 'CMS_VALIDATION', 'Describe the photo before it can be saved.', 'Write what the photo shows, for people who can’t see it.', { field: altName });
      db.media ||= {};
      db.media[img.url] = { width: img.width, height: img.height, name: v.name };
      values[name] = img.url;
    }
  }
  const invalid = validate(resource, values, row);
  if (invalid) return invalid;
  const before = clone(row);
  Object.assign(row, values);
  row.version += 1;
  const fields = diffFields(resource, before, row);
  if (fields.length) {
    db.meta[`${resource}:${pk}`] = { author: user.name, channel: 'admin', at: nowIso() };
    audit(user, 'admin', itemIdFor(resource, row, fields.map((f) => f.name)), values.is_published === false ? 'hidden' : 'changed', fields);
  }
  save();
  return json(200, { ...row });
}

// --------------------------------------------------------------- publish --

function publishView(p) {
  const f = db.flags;
  const elapsed = Date.now() - p.created;
  let status = 'queued';
  let step = 'Waiting to start';
  let message = '';
  if (p.final) return p.final;
  if (elapsed > 1200) {
    status = 'building';
    step = 'Building the site';
  }
  if (elapsed > 3200) {
    if (f.agentOffline) {
      return { id: p.id, status: 'ready_for_upload', step: 'Waiting for upload machine', message: '', live_at: null, agent_last_seen: f.agentLastSeen };
    }
    status = 'uploading';
    step = 'Uploading to the server';
  }
  if (elapsed > 5200) {
    if (p.fail) {
      p.final = { id: p.id, status: 'failed', step: 'Uploading to the server', message: p.fail, live_at: null, agent_last_seen: nowIso() };
    } else {
      const at = nowIso();
      db.published = clone(db.rows);
      db.meta = {};
      db.reviewRequest = null;
      db.snapshots.unshift({ id: p.version, snapshot_id: `${at}-${rid().slice(0, 6)}`, published_at: at, published_by: p.by, note: `${p.count} change${p.count === 1 ? '' : 's'}`, rows: clone(db.rows) });
      p.final = { id: p.id, status: 'live', step: 'Live', message: '', live_at: at, agent_last_seen: at };
    }
    save();
    return p.final;
  }
  return { id: p.id, status, step, message, live_at: null, agent_last_seen: f.agentOffline ? f.agentLastSeen : nowIso() };
}

function shrinkCheck() {
  for (const [res, map] of Object.entries(db.published)) {
    if (SINGLETON_RESOURCES.includes(res)) continue;
    const before = Object.values(map).filter((r) => r.is_published !== false).length;
    const after = Object.values(db.rows[res] || {}).filter((r) => r.is_published !== false).length;
    if (before >= 3 && after < before * 0.7) return { resource: res, before, after };
  }
  return null;
}

// ---------------------------------------------------------------- router --

async function route(method, path, body) {
  load();
  const s = session();
  const user = s && db.users.find((u) => u.id === s.userId && u.is_active);
  if (method !== 'GET' && path !== '/auth/csrf/') {
    const sent = body?.__csrf;
    if (!sent || sent !== csrfCookie()) return json(403, { detail: 'CSRF Failed: CSRF token missing or incorrect.' });
  }

  // ---- auth
  if (path === '/auth/csrf/') {
    return json(200, { csrfToken: csrfCookie() || setCsrfCookie() });
  }
  if (path === '/auth/login/' && method === 'POST') {
    const { username = '', password = '' } = body.data || {};
    const key = username.toLowerCase();
    if ((db.failedLogins[key] || 0) >= 5)
      return fail(429, 'CMS_RATE_LIMITED', 'Sign-in for this account is paused for 15 minutes after 5 attempts that didn’t match.', 'Wait 15 minutes, or ask an Admin to unlock the account.', { locked_until: new Date(Date.now() + 15 * 60000).toISOString() });
    const u = db.users.find((x) => x.username === key && x.is_active);
    if (!u || password !== TEST_PASSWORD) {
      db.failedLogins[key] = (db.failedLogins[key] || 0) + 1;
      save();
      const left = 5 - db.failedLogins[key];
      return fail(400, 'CMS_VALIDATION', 'That username and password don’t match.', left <= 2 ? `${left} more attempt${left === 1 ? '' : 's'} before sign-in is paused for 15 minutes.` : 'Check both and try again.', { attempts_left: left });
    }
    db.failedLogins[key] = 0;
    save();
    setSession({ userId: u.id, stage: u.mfa_enrolled ? 'mfa' : 'setup' });
    return json(200, u.mfa_enrolled ? { mfa_required: true } : { mfa_setup_required: true });
  }
  if (path === '/auth/mfa/' && method === 'POST') {
    if (!s || s.stage !== 'mfa') return fail(401, 'CMS_UNAUTHENTICATED', 'Your sign-in timed out.', 'Sign in again.');
    const code = String(body.data?.code || '').replace(/\s/g, '');
    if (code !== TEST_CODE && !RECOVERY.includes(code)) return fail(400, 'CMS_VALIDATION', 'That code didn’t match.', 'Codes change every 30 seconds. Enter the newest one.', { field: 'code' });
    setSession({ userId: s.userId, stage: 'ok' });
    return json(200, { ...me(db.users.find((u) => u.id === s.userId)), csrfToken: setCsrfCookie() });
  }
  if (path === '/auth/mfa/enrol/' || path === '/auth/mfa/enrol/confirm/') {
    if (!s || s.stage !== 'setup') return fail(401, 'CMS_UNAUTHENTICATED', 'Your sign-in timed out.', 'Sign in again.');
    const u = db.users.find((x) => x.id === s.userId);
    if (path === '/auth/mfa/enrol/') return json(200, { qr_svg: null, qr_data_uri: null, otpauth_uri: `otpauth://totp/CRTDH%20CMS:${u.username}?secret=JBSWY3DPEHPK3PXP&issuer=CRTDH%20CMS`, secret: 'JBSWY3DPEHPK3PXP' });
    const code = String(body.data?.code || '').replace(/\s/g, '');
    if (code !== TEST_CODE) return fail(400, 'CMS_VALIDATION', 'That code didn’t match.', 'Check the app shows “CRTDH CMS”, then enter its newest code.', { field: 'code' });
    u.mfa_enrolled = true;
    save();
    setSession({ userId: u.id, stage: 'ok' });
    return json(200, { ...me(u), csrfToken: setCsrfCookie(), recovery_codes: RECOVERY });
  }
  if (path === '/auth/logout/') {
    setSession(null);
    return json(200, {});
  }
  if (!user || s.stage !== 'ok' || db.flags.expired) {
    if (db.flags.expired) {
      db.flags.expired = false;
      save();
      setSession(null);
    }
    return fail(401, 'CMS_UNAUTHENTICATED', 'You’ve been signed out after 30 minutes without activity.', 'Sign in again. Your unsaved text is kept on this computer.');
  }
  if (path === '/auth/me/') return json(200, me(user));
  if (path === '/auth/password/' && method === 'POST') {
    const v = body.data || {};
    if (v.current_password !== TEST_PASSWORD) return fail(400, 'CMS_VALIDATION', 'That isn’t your current password.', 'Check it and try again.', { field: 'current_password' });
    if (String(v.new_password || '').length < 12) return fail(400, 'CMS_VALIDATION', 'Use at least 12 characters.', 'Choose a longer password.', { field: 'new_password' });
    user.must_change_password = false;
    save();
    return json(200, { ...me(user), csrfToken: setCsrfCookie() });
  }
  if (path === '/auth/sessions/revoke-all/' && method === 'POST') {
    setSession(null);
    return json(200, { revoked: 2 });
  }
  if (path === '/auth/mfa/recovery-codes/' && method === 'POST') {
    if (String(body.data?.code || '') !== TEST_CODE) return fail(400, 'CMS_VALIDATION', 'That code didn’t match.', 'Enter the newest code from the app.', { field: 'code' });
    return json(200, { recovery_codes: RECOVERY });
  }

  // ---- cms
  if (path === '/cms/pages/') {
    const changed = new Set(computeChanges().pages.map((p) => p.page));
    // Same shape as the real API (backend PagesView): site-wide sections under `globals`, not as a page.
    const summary = (x) => ({ id: x.id, label: x.label, kind: x.kind, resource: x.resource });
    const site = PAGES.find((p) => p.id === 'site');
    return json(200, {
      pages: PAGES.filter((p) => p.id !== 'site').map((p) => ({ id: p.id, path: p.path, title: p.title, has_changes: changed.has(p.id), sections: p.sections.map(summary) })),
      globals: { has_changes: changed.has('site'), sections: site ? site.sections.map(summary) : [] },
    });
  }
  let m = path.match(/^\/cms\/pages\/([\w-]+)\/$/);
  if (m) {
    const page = PAGES.find((p) => p.id === m[1]);
    return page ? json(200, pageOut(page)) : fail(404, 'CMS_NOT_FOUND', `There is no page called ${m[1]}.`, 'Choose a page from the list.');
  }
  m = path.match(/^\/cms\/preview\/([\w-]+)\/$/);
  if (m) return json(200, { page: m[1], ...previewOut() });
  if (path === '/cms/changes/') return json(200, computeChanges());
  if (path === '/cms/changes/discard/') {
    const { item_id, session_id } = body.data || {};
    const targets = [];
    if (session_id) {
      for (const [k, v] of Object.entries(db.meta)) if (v.session_id === session_id) targets.push({ key: k, section: null });
    } else if (item_id) {
      const [sectionId, ref] = [item_id.slice(0, item_id.lastIndexOf('.')), item_id.slice(item_id.lastIndexOf('.') + 1)];
      targets.push({ key: ref, section: sectionId });
    }
    for (const { key, section } of targets) {
      const [res, pk] = key.split(':');
      const pub = db.published[res]?.[pk];
      const cur = db.rows[res]?.[pk];
      if (SINGLETON_RESOURCES.includes(res) && section) {
        const sec = PAGES.flatMap((p) => p.sections).find((x) => x.id === section);
        for (const f of sec?.fields || []) for (const n of [f.name, f.alt_field, f.position_field].filter(Boolean)) cur[n] = pub[n];
        cur.version += 1;
      } else if (!pub) delete db.rows[res][pk];
      else db.rows[res][pk] = { ...clone(pub), version: (cur?.version || pub.version) + 1 };
      audit(user, 'admin', item_id || `${res}:${pk}`, 'discarded', []);
      delete db.meta[key];
    }
    save();
    return json(200, { discarded: targets.length, ...computeChanges() });
  }
  if (path === '/cms/review-requests/') {
    db.reviewRequest = { by: user.name, at: nowIso(), note: body.data?.note || '' };
    save();
    // Real API: {id, created_at, notified: <count>, email_sent, message?}; the mock names who was emailed.
    if (db.flags.failReviewEmail) {
      db.flags.failReviewEmail = false;
      save();
      return json(201, { status: 'sent', notified: 0, email_sent: false, message: 'Review requested; the email to Publishers could not be sent.' });
    }
    return json(201, { status: 'sent', email_sent: true, notified: db.users.filter((u) => u.is_active && can(u, 'publisher')).map((u) => u.name) });
  }
  if (path === '/cms/publish/' && method === 'POST') {
    if (!can(user, 'publisher')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Editors can’t publish.', 'Request a review; a Publisher will be emailed.');
    const running = Object.values(db.publishes).find((p) => !publishView(p).status.match(/live|failed|cancelled/));
    if (running) return fail(409, 'CMS_PUBLISH_RUNNING', 'A publish is already running.', 'Wait for it to finish.', { publish_id: running.id });
    const shrink = shrinkCheck();
    if (shrink && !body.data?.confirm_shrink) {
      const label = shrink.resource.replace(/-/g, ' ');
      return fail(422, 'CMS_BUILD_GUARD', `The ${label} list would shrink from ${shrink.before} to ${shrink.after} items.`, 'Check this is intended, then confirm to publish anyway.', { details: [shrink] });
    }
    const id = crypto.randomUUID(); // publish ids are UUIDs (backend-core)
    db.publishes[id] = { id, version: db.nextPublish++, created: Date.now(), by: user.name, count: computeChanges().count, fail: db.flags.failNext };
    db.flags.failNext = null;
    save();
    return json(202, { publish_id: id, status: 'queued' });
  }
  m = path.match(/^\/cms\/publish\/([0-9a-f-]{36})\/(cancel\/)?$/);
  if (m) {
    const p = db.publishes[m[1]];
    if (!p) return fail(404, 'CMS_NOT_FOUND', 'That publish doesn’t exist.', 'Reload the page.');
    if (m[2] && method === 'POST') {
      if (!can(user, 'publisher')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Editors can’t cancel a publish.', 'Ask a Publisher.');
      const st = publishView(p).status;
      if (!['queued', 'ready_for_upload'].includes(st))
        return fail(400, 'CMS_VALIDATION', `This publish is ${st === 'uploading' ? 'already being uploaded' : st} and cannot be cancelled.`, 'Wait for it to finish.');
      p.final = { id: p.id, publish_id: p.id, status: 'cancelled', step: 'Cancelled', message: 'Cancelled; the live site is unchanged.', live_at: null, agent_last_seen: nowIso() };
      save();
      return json(200, p.final);
    }
    return json(200, publishView(p));
  }
  if (path === '/cms/snapshots/')
    return json(200, { snapshots: db.snapshots.map(({ rows: _r, ...x }) => ({ ...x, is_live: x.id === db.snapshots[0]?.id })) });
  m = path.match(/^\/cms\/snapshots\/(\d+)\/restore\/$/);
  if (m) {
    if (!can(user, 'publisher')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Editors can’t restore versions.', 'Ask a Publisher.');
    const snap = db.snapshots.find((x) => String(x.id) === m[1]);
    if (!snap) return fail(404, 'CMS_NOT_FOUND', 'That version no longer exists.', 'Reload the page.');
    for (const [res, map] of Object.entries(snap.rows)) {
      for (const [pk, row] of Object.entries(map)) {
        const cur = db.rows[res]?.[pk];
        if (!cur || JSON.stringify({ ...cur, version: 0 }) !== JSON.stringify({ ...row, version: 0 })) {
          (db.rows[res] ||= {})[pk] = { ...clone(row), version: (cur?.version || 0) + 1 };
          db.meta[`${res}:${pk}`] = { author: user.name, channel: 'admin', at: nowIso(), restored_from: snap.id };
        }
      }
      for (const pk of Object.keys(db.rows[res] || {})) if (!map[pk]) {
        delete db.rows[res][pk];
        db.meta[`${res}:${pk}`] = { author: user.name, channel: 'admin', at: nowIso() };
      }
    }
    save();
    return json(200, { restored: snap.id, ...computeChanges() });
  }
  if (path.startsWith('/cms/audit/')) {
    const itemId = new URLSearchParams(path.split('?')[1]).get('item_id');
    const ref = itemId.slice(itemId.lastIndexOf('.') + 1);
    return json(200, { entries: db.audit.filter((a) => a.item_id === itemId || a.item_id.endsWith(`.${ref}`) || a.item_id === ref).reverse() });
  }

  // ---- contact messages (publisher/admin; stored HTML-escaped)
  // Backup upload (backend apps/publishing/backup.py): a .zip restores as unpublished changes; anything else is refused.
  if (path === '/cms/backup/restore/' && method === 'POST') {
    if (!can(user, 'admin')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Only an Admin can upload a backup.', 'Ask an Admin.');
    const f = body.form?.get?.('file');
    if (!f || !/\.zip$/i.test(f.name || '')) return fail(400, 'CMS_VALIDATION', 'This file is not a CRTDH backup (it is not a zip file).', 'Download a new backup from this CMS and upload that file.');
    if (/damaged/i.test(f.name)) return fail(400, 'CMS_VALIDATION', 'This backup is damaged or was changed after it was downloaded (content checksum does not match).', 'Download a new backup from this CMS and upload that file.');
    return json(200, { restored: 3, photos_written: 0, photos_already_present: 0, backup_created_at: '2026-11-19T10:00:00Z', includes_media: false, pending: 3 });
  }
  // Claude connector access (backend apps/oauth ClaudeAccessView / ClaudeAccessRevokeView).
  if (path === '/cms/claude-access/' && method === 'GET') {
    db.claude ||= {};
    const own = db.claude[user.id] || [];
    const out = { connected: own.length > 0, connections: own, setup: { server_url: 'https://mcp.crtdh.test/mcp', client_id: db.claudeClientId || null } };
    if (can(user, 'admin'))
      out.users = db.users
        .filter((u) => (db.claude[u.id] || []).length)
        .map((u) => ({ user_id: u.id, username: u.username, name: u.name, connections: db.claude[u.id] }));
    return json(200, out);
  }
  if (path === '/cms/claude-access/new-secret/' && method === 'POST') {
    if (!can(user, 'admin')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Only an Admin can create the Claude client secret.', 'Ask an Admin.');
    db.claudeClientId = db.claudeClientId || 'mock-client-id-4f2a9c';
    return json(200, { server_url: 'https://mcp.crtdh.test/mcp', client_id: db.claudeClientId, client_secret: `mock-secret-${Date.now().toString(36)}` });
  }
  if (path === '/cms/claude-access/revoke/' && method === 'POST') {
    db.claude ||= {};
    const target = body.data?.user_id ?? user.id;
    if (target !== user.id && !can(user, 'admin'))
      return fail(403, 'CMS_FORBIDDEN_ROLE', 'Only an Admin can disconnect Claude for another person.', 'Ask an Admin, or omit user_id to disconnect your own access.');
    const revoked = (db.claude[target] || []).length * 2;
    delete db.claude[target];
    save();
    return json(200, { revoked, user_id: target });
  }
  if (path.startsWith('/contact-messages/')) {
    if (!can(user, 'publisher')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Only Publishers and Admins can read messages.', 'Ask a Publisher.');
    db.messages ||= clone(SEED_MESSAGES);
    if (path === '/contact-messages/' && method === 'GET') return json(200, { count: db.messages.length, next: null, previous: null, results: db.messages });
    m = path.match(/^\/contact-messages\/(\d+)\/$/);
    if (m && method === 'DELETE') {
      db.messages = db.messages.filter((x) => String(x.id) !== m[1]);
      save();
      return new Response(null, { status: 204 });
    }
  }

  // ---- users (addendum A12, matches backend-security accounts/users.py)
  if (path.startsWith('/auth/users/')) {
    if (!can(user, 'admin')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Only Admins can manage users.', 'Ask an Admin.');
    const out = (u) => ({ ...me(u), is_active: u.is_active, last_login: u.last_login });
    if (path === '/auth/users/' && method === 'GET') return json(200, { results: db.users.map(out) });
    const v = body.data || {};
    if (path === '/auth/users/' && method === 'POST') {
      if (!/^[A-Za-z0-9._-]{3,64}$/.test(v.username || '')) return fail(400, 'CMS_VALIDATION', 'Use 3 to 64 letters, digits, dots, dashes or underscores.', 'Change the username.', { field: 'username' });
      if (db.users.some((u) => u.username.toLowerCase() === v.username.toLowerCase())) return fail(400, 'CMS_VALIDATION', 'That username is taken.', 'Choose another username.', { field: 'username' });
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email || '')) return fail(400, 'CMS_VALIDATION', 'Enter a valid email address.', 'Check the email address.', { field: 'email' });
      if (!ROLE_ORDER.includes(v.role)) return fail(400, 'CMS_VALIDATION', 'Pick a role.', 'Pick a role.', { field: 'role' });
      const name = [v.first_name, v.last_name].filter(Boolean).join(' ').trim() || v.username;
      const u = { id: db.nextId++, username: v.username, name, email: v.email, roles: rolesUpTo(v.role), mfa_enrolled: false, must_change_password: true, is_active: true, last_login: null };
      db.users.push(u);
      save();
      return json(201, { ...out(u), temporary_password: 'tmp-Kq7v-Rw2m-Xp9d' });
    }
    m = path.match(/^\/auth\/users\/(\d+)\/(role|deactivate|reset-mfa|reset-password)\/$/);
    const u = m && db.users.find((x) => String(x.id) === m[1]);
    if (!u || method !== 'POST') return fail(404, 'CMS_NOT_FOUND', 'That user no longer exists.', 'Reload the page.');
    const admins = () => db.users.filter((x) => x.is_active && x.roles.includes('admin'));
    if (m[2] === 'deactivate') {
      if (u.id === user.id) return fail(400, 'CMS_VALIDATION', 'You cannot deactivate yourself.', 'Ask another admin.');
      if (u.roles.includes('admin') && admins().length <= 1) return fail(400, 'CMS_VALIDATION', 'This is the last admin.', 'Make someone else admin first.');
      u.is_active = false;
    } else if (m[2] === 'role') {
      if (!ROLE_ORDER.includes(v.role)) return fail(400, 'CMS_VALIDATION', 'Pick a role.', 'Pick a role.', { field: 'role' });
      if (u.roles.includes('admin') && v.role !== 'admin' && admins().length <= 1) return fail(400, 'CMS_VALIDATION', 'This is the last admin.', 'Make someone else admin first.');
      u.roles = rolesUpTo(v.role);
    } else {
      // reset-mfa and reset-password both issue a temporary password (backend-security).
      if (u.id === user.id) return fail(400, 'CMS_VALIDATION', 'Use the change-password screen for your own account.', 'Pick another user.');
      if (m[2] === 'reset-mfa') u.mfa_enrolled = false;
      u.must_change_password = true;
      save();
      return json(200, { ...out(u), temporary_password: 'tmp-Hn4c-Lz8q-Wb3t' });
    }
    save();
    return json(200, out(u));
  }

  // ---- content
  m = path.match(/^\/([\w-]+)\/(?:(\d+)\/)?(reorder\/)?$/);
  if (m) {
    const [, resource, pkRaw, reorder] = m;
    if (!db.rows[resource]) return fail(404, 'CMS_NOT_FOUND', `Unknown resource ${resource}.`, 'Reload the page.');
    const single = SINGLETON_RESOURCES.includes(resource);
    const pk = single ? Object.keys(db.rows[resource])[0] : pkRaw;
    if (reorder && method === 'POST') {
      const ids = body.data?.order || [];
      ids.forEach((id, i) => {
        const r = db.rows[resource][id];
        if (r && r.order !== i) {
          const before = r.order;
          r.order = i;
          r.version += 1;
          db.meta[`${resource}:${id}`] = { author: user.name, channel: 'admin', at: nowIso() };
          audit(user, 'admin', itemIdFor(resource, r), 'moved', [{ name: 'order', before, after: i }]);
        }
      });
      save();
      return json(200, { order: ids });
    }
    if (method === 'GET' && !pk) return json(200, sortRows(Object.values(db.rows[resource])));
    if (method === 'GET') return db.rows[resource][pk] ? json(200, db.rows[resource][pk]) : fail(404, 'CMS_NOT_FOUND', 'Not found.', 'Reload.');
    if (method === 'POST' && !pk) {
      const values = { ...(body.data || {}) };
      const id = db.nextId++;
      const siblings = Object.values(db.rows[resource]);
      const row = prepRow(resource, { id, order: siblings.length ? Math.max(...siblings.map((r) => r.order ?? 0)) + 1 : 0, ...values });
      row.id = id;
      db.rows[resource][id] = row;
      db.meta[`${resource}:${id}`] = { author: user.name, channel: 'admin', at: nowIso() };
      audit(user, 'admin', itemIdFor(resource, row), 'added', []);
      save();
      return json(201, row);
    }
    if (method === 'PATCH') return patchRow(user, resource, pk, body.form || body.data);
    if (method === 'DELETE') {
      if (!can(user, 'publisher')) return fail(403, 'CMS_FORBIDDEN_ROLE', 'Editors can’t delete items.', 'Hide it instead, or ask a Publisher.');
      const row = db.rows[resource][pk];
      if (!row) return fail(404, 'CMS_NOT_FOUND', 'Not found.', 'Reload.');
      audit(user, 'admin', itemIdFor(resource, row), 'removed', []);
      delete db.rows[resource][pk];
      db.meta[`${resource}:${pk}`] = { author: user.name, channel: 'admin', at: nowIso() };
      save();
      return json(204);
    }
  }
  return fail(404, 'CMS_NOT_FOUND', `No such endpoint: ${method} ${path}`, 'Check the contract.');
}

// ------------------------------------------------------------ transport --

export async function mockFetch(url, init = {}) {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) throw new TypeError('Failed to fetch');
  if (window.__crtdhMockOffline) throw new TypeError('Failed to fetch');
  const path = url.replace(/^.*\/api\/v1/, '');
  const method = (init.method || 'GET').toUpperCase();
  const body = { __csrf: init.headers?.['X-CSRFToken'] };
  if (init.body instanceof FormData) body.form = init.body;
  else if (init.body) body.data = JSON.parse(init.body);
  const slow = path.startsWith('/cms/publish/') && method === 'GET' ? 60 : 140 + Math.random() * 220;
  await delay(window.__crtdhMockLatency ?? slow);
  const res = await route(method, path, body);
  return res;
}

// Test and demo hooks. Only exist in mock builds.
if (typeof window !== 'undefined') {
  window.__crtdhMock = {
    reset() {
      sessionStorage.removeItem(DB_KEY);
      db = null;
      load();
      save();
    },
    // Someone else edits a row (drives the stale-version conflict).
    otherUserEdits(resource, pk, values, by = 'Priya Sen') {
      load();
      const map = db.rows[resource];
      const key = pk ?? Object.keys(map)[0];
      const row = map[key];
      const before = clone(row);
      Object.assign(row, values);
      row.version += 1;
      db.meta[`${resource}:${key}`] = { author: by, channel: 'admin', at: nowIso() };
      db.audit.push({ item_id: itemIdFor(resource, row, Object.keys(values)), at: nowIso(), author: by, channel: 'admin', action: 'changed', fields: diffFields(resource, before, row) });
      save();
      return row.version;
    },
    setAgentOffline(v = true) {
      load();
      db.flags.agentOffline = v;
      save();
    },
    failNextPublish(message = 'The server refused the upload: disk quota exceeded (98% of 2 GB used).') {
      load();
      db.flags.failNext = message;
      save();
    },
    failNextReviewEmail() {
      load();
      db.flags.failReviewEmail = true;
      save();
    },
    expireSession() {
      load();
      db.flags.expired = true;
      save();
    },
    setOffline(v = true) {
      window.__crtdhMockOffline = v;
      window.dispatchEvent(new Event(v ? 'offline' : 'online'));
    },
    state: () => load(),
  };
}
