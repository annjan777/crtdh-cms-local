import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { ImageOff, Plus } from 'lucide-react';
import ConfirmDialog from '../components/ConfirmDialog';
import SortableList from '../components/SortableList';
import EmptyState from '../components/EmptyState';
import { SkeletonTable } from '../components/Skeleton';
import { deleteResource, listResource, reorderResource } from '../api/resources';
import { getResourceSchema } from '../resources/schemas';
import { getIcon } from '../resources/icons';
import { useToast } from '../context/ToastContext';

function stripHtml(html) {
  if (!html) return '';
  const text = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  return text.length > 120 ? `${text.slice(0, 120)}…` : text;
}

function fieldFor(schema, columnKey) {
  return schema.fields.find((f) => f.name === columnKey);
}

function Cell({ schema, columnKey, item }) {
  const field = fieldFor(schema, columnKey);
  const value = item[columnKey];

  if (field?.type === 'image') {
    return value ? (
      <img src={value} alt="" className="thumb" />
    ) : (
      <span className="thumb thumb-placeholder">
        <ImageOff size={16} aria-hidden="true" />
      </span>
    );
  }
  if (field?.type === 'richtext') {
    return <span>{stripHtml(value)}</span>;
  }
  if (value === null || value === undefined || value === '') {
    return <span className="cell-muted">—</span>;
  }
  return <span>{String(value)}</span>;
}

// Generic list screen for any resource in RESOURCE_SCHEMAS: a table (or,
// for orderable resources, a drag-and-drop list) with create/edit/delete.
// This one component renders every top-level resource in the contract —
// see resources/schemas.js for the per-resource config it reads.
export default function ResourceListPage() {
  const { resourceKey } = useParams();
  const schema = getResourceSchema(resourceKey);
  const toast = useToast();

  const [items, setItems] = useState(null);
  const [error, setError] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [reordering, setReordering] = useState(false);

  useEffect(() => {
    if (!schema) return;
    setItems(null);
    setError('');
    listResource(schema.endpoint)
      .then(setItems)
      .catch(() => setError('Could not load this resource.'));
  }, [schema]);

  const columns = useMemo(() => schema?.listColumns || schema?.fields.map((f) => f.name) || [], [schema]);

  if (!schema) {
    return <Navigate to="/" replace />;
  }

  const singular = schema.label.replace(/s$/, '');
  const Icon = getIcon(schema.icon);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteResource(schema.endpoint, pendingDelete.id);
      setItems((prev) => prev.filter((i) => i.id !== pendingDelete.id));
      setPendingDelete(null);
      toast.success(`${singular} deleted.`);
    } catch {
      toast.error(`Could not delete this ${singular.toLowerCase()}.`);
    } finally {
      setDeleting(false);
    }
  }

  async function handleReorder(newItems) {
    setItems(newItems);
    setReordering(true);
    try {
      await reorderResource(schema.endpoint, newItems.map((i) => i.id));
    } catch {
      toast.error('Could not save the new order.');
    } finally {
      setReordering(false);
    }
  }

  function renderRow(item) {
    return (
      <div className="row-grid" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0,1fr)) auto` }}>
        {columns.map((col) => (
          <div key={col} className="row-cell">
            <Cell schema={schema} columnKey={col} item={item} />
          </div>
        ))}
        <div className="row-actions">
          <Link to={`/resources/${schema.key}/${item.id}`} className="btn btn-ghost btn-small">
            Edit
          </Link>
          <button type="button" className="btn btn-danger btn-small" onClick={() => setPendingDelete(item)}>
            Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <Icon size={20} className="page-title-icon" aria-hidden="true" />
            {schema.label}
          </h1>
          {schema.orderable ? (
            <p className="page-lead">Drag rows by the handle to reorder{reordering ? ' — saving…' : '.'}</p>
          ) : (
            items && <p className="page-lead">{items.length} {items.length === 1 ? 'item' : 'items'}</p>
          )}
        </div>
        <Link to={`/resources/${schema.key}/new`} className="btn btn-primary">
          <Plus size={16} aria-hidden="true" />
          Add {singular}
        </Link>
      </div>

      {error && <div className="form-error">{error}</div>}

      {items === null ? (
        <SkeletonTable columns={columns.length} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Icon}
          title={`No ${schema.label.toLowerCase()} yet`}
          description={`Add the first ${singular.toLowerCase()} to get this section showing on the live site.`}
          actionLabel={`Add ${singular}`}
          actionTo={`/resources/${schema.key}/new`}
        />
      ) : schema.orderable ? (
        <>
          <div
            className="row-grid row-grid-head"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0,1fr)) auto` }}
          >
            {columns.map((col) => (
              <div key={col} className="row-cell">
                {fieldFor(schema, col)?.label || col}
              </div>
            ))}
            <div />
          </div>
          <SortableList items={items} onReorder={handleReorder} renderItem={renderRow} />
        </>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{fieldFor(schema, col)?.label || col}</th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                {columns.map((col) => (
                  <td key={col}>
                    <Cell schema={schema} columnKey={col} item={item} />
                  </td>
                ))}
                <td className="row-actions">
                  <Link to={`/resources/${schema.key}/${item.id}`} className="btn btn-ghost btn-small">
                    Edit
                  </Link>
                  <button type="button" className="btn btn-danger btn-small" onClick={() => setPendingDelete(item)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        title={`Delete ${singular}`}
        message="This cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        busy={deleting}
      />
    </div>
  );
}
