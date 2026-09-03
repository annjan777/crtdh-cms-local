import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import ConfirmDialog from './ConfirmDialog';
import EmptyState from './EmptyState';
import FormField from './FormField';
import SortableList from './SortableList';
import { createResource, deleteResource, reorderResource, updateResource } from '../api/resources';
import { useToast } from '../context/ToastContext';

function emptyValues(fields) {
  const values = {};
  fields.forEach((f) => {
    values[f.name] = f.type === 'image' || f.type === 'file' ? null : '';
  });
  return values;
}

function ChildRow({ child, item, onSaved, onDeleteRequest }) {
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(() => {
    const v = {};
    child.fields.forEach((f) => {
      v[f.name] = item[f.name] ?? (f.type === 'image' || f.type === 'file' ? null : '');
    });
    return v;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSave() {
    setSaving(true);
    setError('');
    try {
      const updated = await updateResource(child.endpoint, item.id, values);
      onSaved(updated);
      setEditing(false);
    } catch {
      setError('Could not save this item.');
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    const imageField = child.fields.find((f) => f.type === 'image');
    const textFields = child.fields.filter((f) => f.type !== 'image' && f.type !== 'file');
    return (
      <div className="child-row-summary">
        {imageField && item[imageField.name] && <img src={item[imageField.name]} alt="" className="thumb-sm" />}
        <div className="child-row-text">
          {textFields.map((f) => (
            <span key={f.name} className="child-row-field">
              {item[f.name] || <em className="cell-muted">—</em>}
            </span>
          ))}
        </div>
        <div className="child-row-actions">
          <button type="button" className="btn btn-ghost btn-small" onClick={() => setEditing(true)}>
            Edit
          </button>
          <button type="button" className="btn btn-danger btn-small" onClick={() => onDeleteRequest(item)}>
            Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="child-row-form">
      {child.fields.map((f) => (
        <div className="form-row" key={f.name}>
          <label>{f.label}</label>
          <FormField field={f} value={values[f.name]} onChange={(v) => setValues((prev) => ({ ...prev, [f.name]: v }))} />
        </div>
      ))}
      {error && <div className="form-error">{error}</div>}
      <div className="child-row-actions">
        <button type="button" className="btn btn-primary btn-small" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button type="button" className="btn btn-ghost btn-small" onClick={() => setEditing(false)} disabled={saving}>
          Cancel
        </button>
      </div>
    </div>
  );
}

// Manages one nested child collection (e.g. Innovation → InnovationImage)
// inline on the parent's edit screen: add/edit/delete/reorder without
// leaving the page. Mutations go straight to the child's own top-level
// endpoint (per the contract) with the parent FK set — the parent object
// itself is never touched by these calls.
export default function ChildResourceManager({ parentId, parentField, child, initialItems }) {
  const toast = useToast();
  const [items, setItems] = useState(initialItems || []);
  const [adding, setAdding] = useState(false);
  const [newValues, setNewValues] = useState(() => emptyValues(child.fields));
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

  async function handleAdd() {
    setCreating(true);
    setCreateError('');
    try {
      const created = await createResource(child.endpoint, { ...newValues, [parentField]: parentId });
      setItems((prev) => [...prev, created]);
      setNewValues(emptyValues(child.fields));
      setAdding(false);
      toast.success(`${child.label.replace(/s$/, '')} added.`);
    } catch {
      setCreateError('Could not add this item — check required fields.');
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteResource(child.endpoint, pendingDelete.id);
      setItems((prev) => prev.filter((i) => i.id !== pendingDelete.id));
      setPendingDelete(null);
      toast.success('Deleted.');
    } catch {
      setError('Could not delete this item.');
      toast.error('Could not delete this item.');
    } finally {
      setDeleting(false);
    }
  }

  async function handleReorder(newItems) {
    setItems(newItems);
    try {
      await reorderResource(child.endpoint, newItems.map((i) => i.id));
    } catch {
      setError('Could not save the new order.');
      toast.error('Could not save the new order.');
    }
  }

  function updateItem(updated) {
    setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
  }

  return (
    <div className="child-manager">
      <div className="child-manager-header">
        <h3>{child.label}</h3>
        <button type="button" className="btn btn-ghost btn-small" onClick={() => setAdding((a) => !a)}>
          {adding ? (
            <>
              <X size={14} aria-hidden="true" />
              Cancel
            </>
          ) : (
            <>
              <Plus size={14} aria-hidden="true" />
              Add {child.label.replace(/s$/, '')}
            </>
          )}
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      {adding && (
        <div className="child-row-form child-row-form-new">
          {child.fields.map((f) => (
            <div className="form-row" key={f.name}>
              <label>{f.label}</label>
              <FormField
                field={f}
                value={newValues[f.name]}
                onChange={(v) => setNewValues((prev) => ({ ...prev, [f.name]: v }))}
              />
            </div>
          ))}
          {createError && <div className="form-error">{createError}</div>}
          <div className="child-row-actions">
            <button type="button" className="btn btn-primary btn-small" onClick={handleAdd} disabled={creating}>
              {creating ? 'Adding…' : 'Add'}
            </button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState compact title="None yet" description={`Add the first ${child.label.replace(/s$/, '').toLowerCase()}.`} />
      ) : child.orderable ? (
        <SortableList
          items={items}
          onReorder={handleReorder}
          renderItem={(item) => (
            <ChildRow child={child} item={item} onSaved={updateItem} onDeleteRequest={setPendingDelete} />
          )}
        />
      ) : (
        <div className="sortable-list">
          {items.map((item) => (
            <div className="sortable-row sortable-row-static" key={item.id}>
              <div className="sortable-row-content">
                <ChildRow child={child} item={item} onSaved={updateItem} onDeleteRequest={setPendingDelete} />
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        title={`Delete ${child.label.replace(/s$/, '')}`}
        message="This cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        busy={deleting}
      />
    </div>
  );
}
