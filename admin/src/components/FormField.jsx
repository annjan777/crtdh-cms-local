import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import ImageUploadField from './ImageUploadField';
import RichTextEditor from './RichTextEditor';

// Renders one form control from a schema field definition. This is the
// single place that maps a field `type` to an input — every resource's
// create/edit form is built by mapping its schema.fields through this.
export default function FormField({ field, value, onChange }) {
  const [options, setOptions] = useState(field.options || []);
  const [loadingOptions, setLoadingOptions] = useState(!!field.optionsEndpoint);

  useEffect(() => {
    let cancelled = false;
    if (field.optionsEndpoint) {
      setLoadingOptions(true);
      apiClient
        .get(field.optionsEndpoint)
        .then(({ data }) => {
          if (cancelled) return;
          const results = Array.isArray(data) ? data : data.results;
          setOptions(results || []);
        })
        .catch(() => {
          if (!cancelled) setOptions([]);
        })
        .finally(() => {
          if (!cancelled) setLoadingOptions(false);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [field.optionsEndpoint]);

  const inputId = `field-${field.name}`;

  switch (field.type) {
    case 'textarea':
      return (
        <textarea
          id={inputId}
          className="input"
          rows={4}
          required={field.required}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
        />
      );

    case 'richtext':
      return <RichTextEditor value={value} onChange={onChange} />;

    case 'number':
      return (
        <input
          id={inputId}
          type="number"
          className="input"
          required={field.required}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
        />
      );

    case 'select': {
      const isStatic = !field.optionsEndpoint;
      return (
        <select
          id={inputId}
          className="input"
          required={field.required}
          value={value ?? ''}
          disabled={!isStatic && loadingOptions}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="" disabled>
            {loadingOptions ? 'Loading…' : 'Select…'}
          </option>
          {isStatic
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : options.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt[field.optionLabel] ?? opt.id}
                </option>
              ))}
        </select>
      );
    }

    case 'image':
      return <ImageUploadField value={value} onChange={onChange} isImage required={field.required} />;

    case 'file':
      return <ImageUploadField value={value} onChange={onChange} isImage={false} required={field.required} />;

    case 'text':
    default:
      return (
        <input
          id={inputId}
          type="text"
          className="input"
          required={field.required}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
        />
      );
  }
}
