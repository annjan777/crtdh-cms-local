// State for one open page: its sections and items, the editable records,
// autosave (1 s after typing stops, with expected_version), local drafts for
// offline and sign-out, and the preview data the canvas renders.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { cms, content } from '../api/cms.js';
import { useChanges } from '../shell/ChangesContext.jsx';
import { validateField } from './validate.js';

const EditorContext = createContext(null);
const DRAFT_PREFIX = 'crtdh-draft:';
const AUTOSAVE_MS = 1000;

const keyOf = (resource, pk) => `${resource}:${pk}`;

function readDraft(key) {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_PREFIX + key) || 'null');
  } catch {
    return null;
  }
}
function writeDraft(key, values, baseVersion) {
  try {
    localStorage.setItem(DRAFT_PREFIX + key, JSON.stringify({ values, base_version: baseVersion, at: new Date().toISOString() }));
  } catch {
    /* storage full: the in-memory copy still exists */
  }
}
function clearDraft(key) {
  localStorage.removeItem(DRAFT_PREFIX + key);
}

// Every field definition by resource, so autosave can validate.
function fieldIndex(page) {
  const idx = {};
  const add = (resource, fields) => {
    for (const f of fields) {
      (idx[resource] ||= {})[f.name] = f;
      if (f.alt_field) idx[resource][f.alt_field] = { name: f.alt_field, type: 'text', label: 'Photo description', max: 200 };
      if (f.position_field) idx[resource][f.position_field] = { name: f.position_field, type: 'text', label: 'Focus point' };
    }
  };
  for (const s of page?.sections || []) {
    add(s.resource, s.fields);
    for (const c of s.children || []) add(c.resource, c.fields);
  }
  return idx;
}

function recordsFrom(page, prev = {}) {
  const out = {};
  const take = (resource, item) => {
    const key = keyOf(resource, item.pk);
    const old = prev[key];
    const busy = old && ['dirty', 'saving', 'offline', 'error', 'conflict'].includes(old.status);
    out[key] = busy
      ? { ...old, media: item.media }
      : { key, resource, pk: item.pk, itemId: item.item_id, version: item.version, values: { ...item.values }, saved: { ...item.values }, media: item.media, status: old?.status === 'saved' ? 'saved' : 'idle', error: null };
  };
  for (const s of page.sections)
    for (const item of s.items) {
      take(s.resource, item);
      for (const [res, kids] of Object.entries(item.children || {})) for (const k of kids) take(res, k);
    }
  return out;
}

export function EditorProvider({ pageId, children }) {
  const { refresh: refreshChanges } = useChanges();
  const [page, setPage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [records, setRecords] = useState({});
  const [restored, setRestored] = useState(0);
  const [online, setOnline] = useState(typeof navigator === 'undefined' ? true : navigator.onLine);
  const recRef = useRef(records);
  const timers = useRef({});
  const inflight = useRef({});
  const fieldsRef = useRef({});

  // Synchronous against recRef so autosave reads what it just wrote.
  const patchRecord = useCallback((key, fn) => {
    const rs = recRef.current;
    if (!rs[key]) return;
    const next = { ...rs, [key]: fn(rs[key]) };
    recRef.current = next;
    setRecords(next);
  }, []);

  const loadPreview = useCallback(async () => {
    try {
      setPreview(await cms.preview(pageId));
    } catch {
      /* the canvas shows its own error state */
    }
  }, [pageId]);

  const load = useCallback(
    async (opts = {}) => {
      if (!opts.quiet) setLoadError(null);
      try {
        const [p, pv] = await Promise.all([cms.page(pageId), cms.preview(pageId)]);
        fieldsRef.current = fieldIndex(p);
        setPage(p);
        setPreview(pv);
        const recs = recordsFrom(p, opts.keep ? recRef.current : {});
        // Restore text kept on this computer (offline, signed out, closed tab).
        let n = 0;
        if (!opts.keep) {
          for (const r of Object.values(recs)) {
            const d = readDraft(r.key);
            if (!d) continue;
            r.values = { ...r.values, ...d.values };
            r.version = d.base_version ?? r.version;
            r.status = 'dirty';
            n += 1;
          }
        }
        recRef.current = recs;
        setRecords(recs);
        if (n) {
          setRestored(n);
          for (const r of Object.values(recs)) if (r.status === 'dirty') schedule(r.key, 50);
        }
      } catch (err) {
        if (!opts.quiet) setLoadError(err);
      }
    },
    // schedule is stable (defined below with refs only)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pageId],
  );

  useEffect(() => {
    setPage(null);
    setPreview(null);
    setRestored(0);
    load();
    const t = timers.current;
    return () => Object.values(t).forEach(clearTimeout);
  }, [load]);

  const save = useCallback(
    async (key) => {
      const r = recRef.current[key];
      if (!r) return;
      if (inflight.current[key]) {
        inflight.current[key].again = true;
        return;
      }
      const fields = fieldsRef.current[r.resource] || {};
      const changed = {};
      const invalid = {};
      for (const [k, v] of Object.entries(r.values)) {
        if (JSON.stringify(v ?? '') === JSON.stringify(r.saved[k] ?? '')) continue;
        const err = fields[k] ? validateField(fields[k], v) : null;
        if (err) invalid[k] = err;
        else changed[k] = v;
      }
      if (!Object.keys(changed).length) {
        patchRecord(key, (x) => ({ ...x, status: Object.keys(invalid).length ? 'invalid' : x.status === 'dirty' ? 'saved' : x.status }));
        if (!Object.keys(invalid).length) clearDraft(key);
        return;
      }
      inflight.current[key] = { again: false };
      patchRecord(key, (x) => ({ ...x, status: 'saving', error: null }));
      try {
        const row = await content.update(r.resource, r.pk, changed, r.version);
        patchRecord(key, (x) => {
          const saved = { ...x.saved, ...changed };
          const stillDirty = Object.entries(x.values).some(([k, v]) => JSON.stringify(v ?? '') !== JSON.stringify(saved[k] ?? '') && !(fields[k] && validateField(fields[k], v)));
          return { ...x, saved, version: row?.version ?? x.version + 1, status: stillDirty ? 'dirty' : 'saved', error: null, savedAt: Date.now() };
        });
        const now = recRef.current[key];
        if (now && now.status === 'saved') clearDraft(key);
        refreshChanges();
        if ('is_published' in changed || 'order' in changed) loadPreview();
      } catch (err) {
        const status = err.code === 'NETWORK' ? 'offline' : err.code === 'CMS_STALE_VERSION' ? 'conflict' : err.code === 'CMS_UNAUTHENTICATED' ? 'dirty' : 'error';
        patchRecord(key, (x) => ({ ...x, status, error: err }));
      } finally {
        const again = inflight.current[key]?.again;
        delete inflight.current[key];
        const now = recRef.current[key];
        if (again || now?.status === 'dirty') schedule(key, again ? 0 : AUTOSAVE_MS);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [patchRecord, refreshChanges, loadPreview],
  );

  const saveRef = useRef(save);
  saveRef.current = save;
  function schedule(key, ms = AUTOSAVE_MS) {
    clearTimeout(timers.current[key]);
    timers.current[key] = setTimeout(() => saveRef.current(key), ms);
  }

  const edit = useCallback(
    (key, patch, { immediate = false } = {}) => {
      const conflict = recRef.current[key]?.status === 'conflict';
      patchRecord(key, (x) => {
        const values = { ...x.values, ...patch };
        const changed = Object.fromEntries(Object.entries(values).filter(([k, v]) => JSON.stringify(v ?? '') !== JSON.stringify(x.saved[k] ?? '')));
        writeDraft(key, changed, x.version);
        return { ...x, values, status: conflict ? 'conflict' : 'dirty' };
      });
      if (!conflict) schedule(key, immediate ? 0 : AUTOSAVE_MS);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [patchRecord],
  );

  const retry = useCallback((key) => schedule(key, 0), []); // eslint-disable-line react-hooks/exhaustive-deps

  // Back online: save everything kept locally.
  useEffect(() => {
    const on = () => {
      setOnline(true);
      for (const r of Object.values(recRef.current)) if (['offline', 'dirty'].includes(r.status)) schedule(r.key, 0);
    };
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Conflict: drop local text for this record and take the server's copy.
  const reloadRecord = useCallback(
    async (key) => {
      clearDraft(key);
      patchRecord(key, (x) => ({ ...x, status: 'idle', error: null, values: { ...x.saved } }));
      const p = await cms.page(pageId);
      fieldsRef.current = fieldIndex(p);
      setPage(p);
      const fresh = recordsFrom(p, {});
      const next = { ...recRef.current, [key]: fresh[key] || recRef.current[key] };
      recRef.current = next;
      setRecords(next);
      loadPreview();
    },
    [pageId, patchRecord, loadPreview],
  );

  const uploadImage = useCallback(
    async (key, field, file, alt) => {
      const r = recRef.current[key];
      const extra = field.alt_field ? { [field.alt_field]: alt } : {};
      patchRecord(key, (x) => ({ ...x, status: 'saving', error: null }));
      try {
        const row = await content.upload(r.resource, r.pk, field.name, file, extra, r.version);
        patchRecord(key, (x) => ({
          ...x,
          version: row.version,
          values: { ...x.values, [field.name]: row[field.name], ...extra },
          saved: { ...x.saved, [field.name]: row[field.name], ...extra },
          status: 'saved',
          savedAt: Date.now(),
        }));
        await load({ keep: true, quiet: true });
        refreshChanges();
        return null;
      } catch (err) {
        patchRecord(key, (x) => ({ ...x, status: err.code === 'CMS_STALE_VERSION' ? 'conflict' : x.status === 'saving' ? 'idle' : x.status, error: err.code === 'CMS_STALE_VERSION' ? err : null }));
        return err;
      }
    },
    [patchRecord, load, refreshChanges],
  );

  const addItem = useCallback(
    async (resource, values) => {
      const row = await content.create(resource, values);
      await load({ keep: true, quiet: true });
      refreshChanges();
      return row;
    },
    [load, refreshChanges],
  );

  const reorder = useCallback(
    async (resource, ids) => {
      await content.reorder(resource, ids);
      await load({ keep: true, quiet: true });
      refreshChanges();
    },
    [load, refreshChanges],
  );

  const removeItem = useCallback(
    async (resource, pk) => {
      await content.remove(resource, pk);
      clearDraft(keyOf(resource, pk));
      await load({ keep: true, quiet: true });
      refreshChanges();
    },
    [load, refreshChanges],
  );

  // Preview = server preview + values being typed right now.
  const livePreview = useMemo(() => {
    if (!preview) return null;
    const data = { ...preview, singletons: { ...preview.singletons }, collections: { ...preview.collections } };
    for (const r of Object.values(records)) {
      if (data.singletons[r.resource]) data.singletons[r.resource] = { ...data.singletons[r.resource], ...r.values };
      else if (data.collections[r.resource]) data.collections[r.resource] = data.collections[r.resource].map((row) => (row.id === r.pk ? { ...row, ...r.values } : row));
    }
    return data;
  }, [preview, records]);

  const value = useMemo(
    () => ({ pageId, page, preview: livePreview, loadError, records, restored, online, reload: load, edit, retry, reloadRecord, uploadImage, addItem, reorder, removeItem, keyOf, dismissRestored: () => setRestored(0) }),
    [pageId, page, livePreview, loadError, records, restored, online, load, edit, retry, reloadRecord, uploadImage, addItem, reorder, removeItem],
  );
  return <EditorContext.Provider value={value}>{children}</EditorContext.Provider>;
}

export function useEditor() {
  return useContext(EditorContext);
}

export function hasUnsaved(records) {
  return Object.values(records).some((r) => ['dirty', 'saving', 'offline', 'error', 'conflict', 'invalid'].includes(r.status));
}
