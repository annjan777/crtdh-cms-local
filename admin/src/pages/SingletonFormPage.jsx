import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import FormField from '../components/FormField';
import Spinner from '../components/Spinner';
import { useToast } from '../context/ToastContext';
import LivePreviewPane from '../components/LivePreviewPane';

// Generic edit form for a singleton resource (a GET/PATCH endpoint with no
// id in the path and no list — SiteSettings, AboutPage, HomePage all use
// this shape on the backend). Handles both plain-JSON and multipart
// (image/file field present) submissions, same as ResourceFormPage does
// for id-based resources.

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

// File-valued fields are omitted unless the staff member picked a new
// File — this mirrors buildPayload in api/resources.js, so re-saving a
// singleton never clobbers an existing image with an empty value.
function buildSingletonPayload(values, fields) {
  const hasFile = fields.some((f) => values[f.name] instanceof File);
  if (!hasFile) {
    const out = {};
    fields.forEach((f) => {
      if (f.type === 'image' || f.type === 'file') return;
      out[f.name] = values[f.name];
    });
    return out;
  }
  const formData = new FormData();
  fields.forEach((f) => {
    const v = values[f.name];
    if (f.type === 'image' || f.type === 'file') {
      if (v instanceof File) formData.append(f.name, v);
    } else {
      formData.append(f.name, v ?? '');
    }
  });
  return formData;
}

export default function SingletonFormPage({ title, description, icon: Icon, endpoint, fields }) {
  const toast = useToast();
  const [values, setValues] = useState(() => emptyValues(fields));
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    setLoading(true);
    apiClient
      .get(endpoint)
      .then(({ data }) => {
        setItem(data);
        setValues(valuesFromItem(fields, data));
      })
      .catch(() => setError(`Could not load ${title}.`))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = buildSingletonPayload(values, fields);
      const { data } = await apiClient.patch(endpoint, payload);
      setItem(data);
      setValues(valuesFromItem(fields, data));
      setSuccess('Saved.');
      toast.success('Changes saved.');
    } catch (err) {
      const data = err?.response?.data;
      if (data && typeof data === 'object') {
        const firstKey = Object.keys(data)[0];
        const firstMsg = Array.isArray(data[firstKey]) ? data[firstKey][0] : data[firstKey];
        setError(`${firstKey}: ${firstMsg}`);
        toast.error(`Could not save: ${firstKey} — ${firstMsg}`);
      } else {
        setError('Could not save changes.');
        toast.error('Could not save changes.');
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Spinner label={`Loading ${title}…`} />;
  if (!item) return <div className="form-error">{error || `Could not load ${title}.`}</div>;

  const previewType = endpoint.includes('about')
    ? 'about'
    : endpoint.includes('site-settings')
    ? 'site-settings'
    : 'default';

  return (
    <div className="singleton-page-wrap">
      <div className="page-header mb-4">
        <h1>
          {Icon && <Icon size={20} className="page-title-icon" aria-hidden="true" />}
          {title}
        </h1>
        {description && <p className="page-lead">{description}</p>}
      </div>

      <div className="singleton-split-layout">
        <form className="resource-form" onSubmit={handleSubmit}>
          <div className="resource-form-grid">
            {fields.map((field) => {
              const isFull = field.type === 'textarea' || field.type === 'image' || field.type === 'file';
              return (
                <div className={`form-row ${isFull ? 'form-row--full' : ''}`} key={field.name}>
                  <label htmlFor={`field-${field.name}`}>{field.label}</label>
                  <FormField
                    field={field}
                    value={values[field.name]}
                    onChange={(v) => setValues((prev) => ({ ...prev, [field.name]: v }))}
                  />
                  {field.hint && <span className="field-hint">{field.hint}</span>}
                </div>
              );
            })}
          </div>

          {success && <div className="form-success">{success}</div>}
          {error && <div className="form-error">{error}</div>}

          <div className="form-actions mt-4">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>

        <div className="singleton-preview-side">
          <LivePreviewPane type={previewType} data={values} />
        </div>
      </div>
    </div>
  );
}
