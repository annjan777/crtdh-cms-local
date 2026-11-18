// Right column: the selected section's fields, generated from the registry.
import { useEffect, useMemo, useRef, useState } from 'react';
import { History } from 'lucide-react';
import { useAuth } from '../auth/AuthContext.jsx';
import { cms, content } from '../api/cms.js';
import { Banner, CopyButton, Dialog, Spinner, fmtDateTime, relTime } from '../ui/index.jsx';
import { useEditor } from './EditorContext.jsx';
import FieldRenderer from './fields/FieldRenderer.jsx';
import CollectionList, { labelFor } from './CollectionList.jsx';
import { plain } from './validate.js';

const CHANNEL = { admin: 'in the editor', claude: 'through Claude', mcp: 'through Claude', api: 'through the API' };

export function SaveStatus({ records }) {
  const { retry } = useEditor();
  const list = records.filter(Boolean);
  const failed = list.find((r) => r.status === 'error');
  let node = null;
  if (list.some((r) => r.status === 'conflict')) node = <span className="save-status is-bad">Not saved · changed by someone else</span>;
  else if (failed)
    node = (
      <span className="save-status is-bad">
        Couldn’t save —{' '}
        <button type="button" className="link-btn" onClick={() => list.filter((r) => r.status === 'error').forEach((r) => retry(r.key))}>
          retry
        </button>
      </span>
    );
  else if (list.some((r) => r.status === 'offline')) node = <span className="save-status is-warn">Offline · kept on this computer</span>;
  else if (list.some((r) => r.status === 'invalid')) node = <span className="save-status is-warn">Not saved · check the field</span>;
  else if (list.some((r) => r.status === 'saving' || r.status === 'dirty')) node = <span className="save-status">Saving…</span>;
  else if (list.some((r) => r.status === 'saved')) node = <span className="save-status is-ok">Saved · not live yet</span>;
  return (
    <span className="save-slot" aria-live="polite">
      {node}
    </span>
  );
}

function ConflictBox({ record, fields }) {
  const { reloadRecord } = useEditor();
  const e = record.error;
  const mine = Object.entries(record.values)
    .filter(([k, v]) => JSON.stringify(v ?? '') !== JSON.stringify(record.saved[k] ?? ''))
    .map(([k, v]) => `${fields.find((f) => f.name === k)?.label || k}: ${plain(v)}`)
    .join('\n');
  const who = e?.details?.edited_by;
  const when = e?.details?.edited_at;
  return (
    <div className="conflict" role="alert">
      <h3>{who ? `${who} changed this ${relTime(when)}` : 'Someone else changed this'}</h3>
      <p>Your change wasn’t saved, so nothing of theirs was overwritten. Reload to see their version, then apply your change again.</p>
      {mine ? (
        <div className="conflict-mine">
          <p className="field-hint">Your unsaved text</p>
          <pre>{mine}</pre>
        </div>
      ) : null}
      <div className="row-actions">
        <button type="button" className="btn btn-primary" onClick={() => reloadRecord(record.key)}>
          Reload section
        </button>
        {mine ? <CopyButton text={mine} label="Copy my text" className="btn" /> : null}
      </div>
    </div>
  );
}

function AuditTrail({ itemId }) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    if (!open) return;
    setEntries(null);
    cms.audit(itemId).then((r) => setEntries(r.entries || []), setErr);
  }, [open, itemId]);
  return (
    <details className="audit" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>
        <History size={16} aria-hidden="true" /> Edit history
      </summary>
      {err ? <p className="field-error">The history couldn’t be loaded. {err.fix}</p> : null}
      {open && !entries && !err ? <p className="field-hint">Loading…</p> : null}
      {entries && !entries.length ? <p className="field-hint">No edits recorded since this item was created.</p> : null}
      {entries?.length ? (
        <ol className="audit-list">
          {entries.map((a, i) => (
            <li key={i}>
              <p>
                <strong>{a.author}</strong> {a.action} {CHANNEL[a.channel] || ''} · <time dateTime={a.at}>{fmtDateTime(a.at)}</time>
              </p>
              {a.fields?.length ? (
                <ul>
                  {a.fields.slice(0, 4).map((f) => (
                    <li key={f.name} className="field-hint">
                      {f.label || f.name}: “{plain(f.before).slice(0, 60) || 'empty'}” → “{plain(f.after).slice(0, 60) || 'empty'}”
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </details>
  );
}

function useChoices(fields) {
  const [opts, setOpts] = useState({});
  useEffect(() => {
    for (const f of fields)
      if (f.choices_resource && !opts[f.name])
        content.list(f.choices_resource).then((rows) => setOpts((o) => ({ ...o, [f.name]: rows.map((r) => ({ value: r.id, label: r[f.choice_label || 'name'] })) })), () => {});
  }, [fields]); // eslint-disable-line react-hooks/exhaustive-deps
  return opts;
}

function ItemFields({ def, record, item, canDelete, sectionLabel, onDeleted, isChild }) {
  const { edit, uploadImage, removeItem } = useEditor();
  const opts = useChoices(def.fields);
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [delErr, setDelErr] = useState(null);
  if (!record) return null;
  const fieldErr = record.status === 'invalid' || record.status === 'error' ? record.error : null;
  const noun = def.item_noun || def.add_label || 'item';
  const name = labelFor(def, record.values, 0);
  return (
    <div className="item-fields">
      {record.status === 'conflict' ? <ConflictBox record={record} fields={def.fields} /> : null}
      {record.status === 'error' && record.error && !record.error.field ? (
        <Banner tone="danger" actions={<CopyButton text={record.error.supportText?.() || ''} />}>
          {record.error.message} {record.error.fix}
        </Banner>
      ) : null}
      {def.fields.map((f) => (
        <FieldRenderer
          key={f.name}
          field={f}
          record={record}
          options={opts[f.name]}
          serverError={fieldErr?.field === f.name ? fieldErr.message : null}
          onChange={(patch, o) => edit(record.key, patch, o)}
          onUpload={(field, file, alt) => uploadImage(record.key, field, file, alt)}
        />
      ))}
      {'is_published' in record.values ? (
        <div className="field field-switch">
          <label className="switch">
            <input type="checkbox" role="switch" checked={record.values.is_published !== false} onChange={(e) => edit(record.key, { is_published: e.target.checked }, { immediate: true })} />
            <span className="switch-track" aria-hidden="true" />
            <span className="switch-label">Shown on site</span>
          </label>
          <p className="field-hint">{record.values.is_published === false ? `Hidden: this ${noun} stays in the CMS but won’t appear on the site.` : `Turn off to take this ${noun} off the site without deleting it.`}</p>
        </div>
      ) : null}
      {def.children?.map((c) => <ChildList key={c.resource} child={c} parent={item} sectionLabel={sectionLabel} />)}
      {!isChild ? <AuditTrail itemId={item.item_id} /> : null}
      {canDelete ? (
        <div className="danger-zone">
          <button type="button" className="btn btn-danger-text" onClick={() => setConfirm(true)}>
            Delete {noun}
          </button>
        </div>
      ) : null}
      <Dialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={`Delete ${noun} “${name.length > 50 ? `${name.slice(0, 48)}…` : name}”?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(false)}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              aria-busy={deleting || undefined}
              onClick={async () => {
                setDeleting(true);
                setDelErr(null);
                try {
                  await removeItem(def.resource, record.pk);
                  setConfirm(false);
                  onDeleted?.();
                } catch (err) {
                  setDelErr(err);
                } finally {
                  setDeleting(false);
                }
              }}
            >
              {deleting ? <Spinner /> : null}
              Delete {noun}
            </button>
          </>
        }
      >
        <p>It is removed from the CMS. The live site keeps it until the next publish, and you can bring it back by discarding this change on the review screen.</p>
        <p>To take it off the site but keep it, hide it instead.</p>
        {delErr ? <Banner tone="danger">{delErr.message} {delErr.fix}</Banner> : null}
      </Dialog>
    </div>
  );
}

function ChildList({ child, parent }) {
  const { records, addItem, reorder } = useEditor();
  const { canPublish } = useAuth();
  const items = parent.children?.[child.resource] || [];
  const [selected, setSelected] = useState(null);
  const [adding, setAdding] = useState(false);
  const sel = items.find((i) => i.pk === selected);
  async function add() {
    setAdding(true);
    try {
      const row = await addItem(child.resource, { [child.parent_field]: parent.pk, is_published: false });
      setSelected(row.id);
    } finally {
      setAdding(false);
    }
  }
  return (
    <section className="child-list" aria-label={child.label}>
      <h3 className="sub-heading">
        {child.label} <span className="count">{items.length}</span>
      </h3>
      {items.length ? (
        <CollectionList def={child} items={items} records={records} selectedPk={selected} onSelect={(pk) => setSelected(pk === selected ? null : pk)} onReorder={(ids) => reorder(child.resource, ids)} onAdd={add} adding={adding} listLabel={child.label} />
      ) : (
        <div className="empty-inline">
          <p>No {child.label.toLowerCase()} yet.</p>
          <button type="button" className="btn btn-add" onClick={add}>
            Add first {child.add_label}
          </button>
        </div>
      )}
      {sel ? (
        <div className="child-editor">
          <ItemFields def={child} record={records[`${child.resource}:${sel.pk}`]} item={sel} canDelete={canPublish} isChild onDeleted={() => setSelected(null)} />
        </div>
      ) : null}
    </section>
  );
}

export function EmptySection({ section, onAdd, adding }) {
  const noun = section.add_label || 'item';
  return (
    <div className="empty-section">
      <h3>Nothing in {section.label} yet</h3>
      <p>{section.description} The section stays hidden on the site until it has at least one {noun}.</p>
      <button type="button" className="btn btn-primary" onClick={onAdd} aria-busy={adding || undefined}>
        Add first {noun}
      </button>
    </div>
  );
}

export default function FieldPanel({ section, index, total, selectedPk, onSelectItem, pageTitle }) {
  const { records, addItem, reorder } = useEditor();
  const { canPublish } = useAuth();
  const [adding, setAdding] = useState(false);
  const [addErr, setAddErr] = useState(null);
  const headingRef = useRef(null);
  useEffect(() => {
    setAddErr(null);
  }, [section?.id]);

  const items = section?.items || [];
  const isCollection = section?.kind === 'collection';
  const item = isCollection ? items.find((i) => i.pk === selectedPk) || items[0] : items[0];
  const record = item ? records[`${section.resource}:${item.pk}`] : null;
  const shownRecords = useMemo(() => {
    if (!item) return [];
    const list = [record];
    for (const [res, kids] of Object.entries(item.children || {})) for (const k of kids) list.push(records[`${res}:${k.pk}`]);
    return list;
  }, [item, record, records, section]);

  if (!section) return <aside className="field-panel" aria-label="Section fields" />;

  async function add() {
    setAdding(true);
    setAddErr(null);
    try {
      const row = await addItem(section.resource, { ...(section.filter || {}), is_published: false });
      onSelectItem(row.id);
    } catch (err) {
      setAddErr(err);
    } finally {
      setAdding(false);
    }
  }

  const pos = isCollection && item ? items.findIndex((i) => i.pk === item.pk) + 1 : 0;
  const noun = section.item_noun || section.add_label || 'item';

  return (
    <aside className="field-panel" aria-labelledby="panel-title">
      <div className="panel-head">
        <div>
          <h2 id="panel-title" ref={headingRef} tabIndex={-1}>
            {section.label}
          </h2>
          <p className="panel-sub">
            {pageTitle} · section {index + 1} of {total}
            {isCollection && item ? ` · ${noun} ${pos} of ${items.length}` : ''}
          </p>
        </div>
        <SaveStatus records={shownRecords} />
      </div>
      <p className="panel-desc">{section.description}</p>
      {addErr ? <Banner tone="danger">{addErr.message} {addErr.fix}</Banner> : null}
      {isCollection ? (
        items.length ? (
          <>
            <CollectionList def={section} items={items} records={records} selectedPk={item?.pk} onSelect={onSelectItem} onReorder={(ids) => reorder(section.resource, ids)} onAdd={add} adding={adding} listLabel={`${section.label} in order`} />
            {item ? (
              <div className="item-editor" key={item.pk}>
                <h3 className="sub-heading">
                  {labelFor(section, record?.values || item.values, pos - 1)}
                </h3>
                <ItemFields def={section} record={record} item={item} canDelete={canPublish} sectionLabel={section.label} onDeleted={() => onSelectItem(null)} />
              </div>
            ) : null}
          </>
        ) : (
          <EmptySection section={section} onAdd={add} adding={adding} />
        )
      ) : item ? (
        <ItemFields def={section} record={record} item={item} canDelete={false} sectionLabel={section.label} />
      ) : (
        <Banner tone="warn">This section has no stored content. Reload the page; if it stays empty, an Admin needs to check the CMS setup.</Banner>
      )}
    </aside>
  );
}
