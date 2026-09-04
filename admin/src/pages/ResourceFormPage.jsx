import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import ChildResourceManager from '../components/ChildResourceManager';
import FormField from '../components/FormField';
import Spinner from '../components/Spinner';
import { createResource, getResource, updateResource } from '../api/resources';
import { getResourceSchema } from '../resources/schemas';
import { useToast } from '../context/ToastContext';

function emptyValues(fields) {
  const values = {};
  fields.forEach((f) => {
    values[f.name] = f.type === 'image' || f.type === 'file' ? null : '';
  });
  return values;
}

function valuesFromItem(fields, item) {
  const values = {};
  fields.forEach((f) => {
    values[f.name] = item[f.name] ?? (f.type === 'image' || f.type === 'file' ? null : '');
  });
  return values;
}

// Generic create/edit form for any resource in RESOURCE_SCHEMAS. In edit
// mode, if the schema declares `children`, it also renders one
// <ChildResourceManager> per nested collection so staff can manage e.g. an
// Innovation's images without leaving the page.
export default function ResourceFormPage() {
  const { resourceKey, id } = useParams();
  const schema = getResourceSchema(resourceKey);
  const navigate = useNavigate();
  const toast = useToast();
  const isCreate = !id;

  const [values, setValues] = useState(() => (schema ? emptyValues(schema.fields) : {}));
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(!isCreate);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!schema || isCreate) return;
    setLoading(true);
    getResource(schema.endpoint, id)
      .then((data) => {
        setItem(data);
        setValues(valuesFromItem(schema.fields, data));
      })
      .catch(() => setError('Could not load this item.'))
      .finally(() => setLoading(false));
  }, [schema, id, isCreate]);

  if (!schema) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      if (isCreate) {
        const created = await createResource(schema.endpoint, values);
        toast.success(`${schema.label.replace(/s$/, '')} created.`);
        if (schema.children && schema.children.length > 0) {
          // Nested children need a parent id first, so route straight to
          // the edit screen where the child managers render.
          navigate(`/resources/${schema.key}/${created.id}`, { replace: true });
        } else {
          navigate(`/resources/${schema.key}`);
        }
      } else {
        const updated = await updateResource(schema.endpoint, id, values);
        setItem(updated);
        setValues(valuesFromItem(schema.fields, updated));
        setSuccess('Saved.');
        toast.success('Changes saved.');
      }
    } catch (err) {
      const data = err?.response?.data;
      if (data && typeof data === 'object') {
        const firstKey = Object.keys(data)[0];
        const firstMsg = Array.isArray(data[firstKey]) ? data[firstKey][0] : data[firstKey];
        setError(`${firstKey}: ${firstMsg}`);
        toast.error(`Could not save: ${firstKey} — ${firstMsg}`);
      } else {
        setError('Could not save this item.');
        toast.error('Could not save this item.');
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Spinner label="Loading…" />;

  return (
    <div>
      <div className="page-header">
        <h1>
          {isCreate ? `Add ${schema.label.replace(/s$/, '')}` : `Edit ${schema.label.replace(/s$/, '')}`}
        </h1>
        <button type="button" className="btn btn-ghost" onClick={() => navigate(`/resources/${schema.key}`)}>
          <ArrowLeft size={15} aria-hidden="true" />
          Back to list
        </button>
      </div>

      <form className="resource-form" onSubmit={handleSubmit}>
        <div className="resource-form-grid">
          {schema.fields.map((field) => {
            const isFull = field.type === 'textarea' || field.type === 'image' || field.type === 'file' || field.type === 'richtext';
            return (
              <div className={`form-row ${isFull ? 'form-row--full' : ''}`} key={field.name}>
                <label htmlFor={`field-${field.name}`}>
                  {field.label}
                  {field.required && <span className="required-mark"> *</span>}
                </label>
                <FormField field={field} value={values[field.name]} onChange={(v) => setValues((prev) => ({ ...prev, [field.name]: v }))} />
                {field.hint && <span className="field-hint">{field.hint}</span>}
              </div>
            );
          })}
        </div>

        {error && <div className="form-error">{error}</div>}
        {success && <div className="form-success">{success}</div>}

        <div className="form-actions mt-4">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : isCreate ? 'Create' : 'Save changes'}
          </button>
        </div>
      </form>

      {!isCreate && schema.children && item && (
        <div className="child-managers">
          {schema.children.map((child) => (
            <ChildResourceManager
              key={child.key}
              parentId={item.id}
              parentField={child.parentField}
              child={child}
              initialItems={item[child.nestedField] || []}
            />
          ))}
        </div>
      )}
    </div>
  );
}
