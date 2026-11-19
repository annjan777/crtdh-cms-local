// One control per registry field type (contract §2): text, textarea,
// richtext, image, url, date, number, select, boolean. Validation is
// blur-first: nothing turns red while someone is still typing.
import { useEffect, useState } from 'react';
import { Field } from '../../ui/index.jsx';
import { lower, plain, validateField } from '../validate.js';
import RichTextField from './RichTextField.jsx';
import ImageField from './ImageField.jsx';

export const fieldId = (recordKey, name) => `f-${recordKey.replace(/[^a-z0-9]/gi, '-')}-${name}`;

function Counter({ value, max }) {
  if (!max) return null;
  const n = plain(value).length;
  return (
    <span className={`counter${n > max ? ' over' : ''}`} aria-live={n > max ? 'polite' : 'off'}>
      {n} / {max}
    </span>
  );
}

function useBlurValidation(field, value, serverError) {
  const [touched, setTouched] = useState(false);
  const [hide, setHide] = useState(false);
  const err = validateField(field, value);
  const shown = (touched && !hide && err) || serverError || null;
  return {
    error: shown,
    onBlur: () => {
      setTouched(true);
      setHide(false);
    },
    onFocus: () => setHide(true),
  };
}

function hintFor(field) {
  if (field.help) return field.help;
  if (field.type === 'url') return 'A page on this site such as /media, or a full address starting https://.';
  return null;
}

export default function FieldRenderer({ field, record, onChange, options, serverError, onUpload }) {
  const id = fieldId(record.key, field.name);
  const value = record.values[field.name];
  const v = useBlurValidation(field, value, serverError);
  const describedBy = `${id}-msg`;
  const common = {
    id,
    name: field.name,
    'aria-describedby': describedBy,
    'aria-invalid': v.error ? true : undefined,
    'aria-required': field.required || undefined,
    onBlur: v.onBlur,
    onFocus: v.onFocus,
  };
  const set = (val, opts) => onChange({ [field.name]: val }, opts);

  switch (field.type) {
    case 'image':
      return <ImageField field={field} record={record} onChange={onChange} onUpload={onUpload} id={id} />;
    case 'richtext':
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field) || 'Bold, italic, links, lists and small headings.'} error={v.error} aside={<Counter value={value} max={field.max} />}>
          <RichTextField id={id} value={value || ''} onChange={(html) => set(html)} label={field.label} onBlur={v.onBlur} invalid={!!v.error} />
        </Field>
      );
    case 'textarea':
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error} aside={<Counter value={value} max={field.max} />}>
          <AutoTextarea {...common} value={value ?? ''} onChange={(e) => set(e.target.value)} />
        </Field>
      );
    case 'boolean':
      return (
        <div className="field field-switch">
          <label className="switch" htmlFor={id}>
            <input type="checkbox" role="switch" id={id} checked={!!value} aria-describedby={hintFor(field) ? describedBy : undefined} onChange={(e) => set(e.target.checked, { immediate: true })} />
            <span className="switch-track" aria-hidden="true" />
            <span className="switch-label">{field.label}</span>
          </label>
          {hintFor(field) ? (
            <p className="field-hint" id={describedBy}>
              {hintFor(field)}
            </p>
          ) : null}
        </div>
      );
    case 'select': {
      const choices = (options || field.choices || []).map((c) => (typeof c === 'object' ? c : { value: c, label: c.replace(/-/g, ' ').replace(/^\w/, (x) => x.toUpperCase()) }));
      const known = choices.some((c) => String(c.value) === String(value ?? ''));
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error}>
          <select {...common} value={value ?? ''} onChange={(e) => set(field.choices_resource ? Number(e.target.value) : e.target.value, { immediate: true })}>
            {!known ? <option value={value ?? ''}>{value ? String(value) : `Choose ${lower(field.label)}`}</option> : null}
            {choices.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </Field>
      );
    }
    case 'number':
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error}>
          <input {...common} type="text" inputMode="decimal" className="input-short" value={value ?? ''} onChange={(e) => set(e.target.value === '' ? null : e.target.value.replace(/[^\d.-]/g, ''))} />
        </Field>
      );
    case 'date':
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error}>
          <input {...common} type="date" className="input-short" value={value ?? ''} onChange={(e) => set(e.target.value || null)} />
        </Field>
      );
    case 'url':
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error}>
          <input {...common} type="text" inputMode="url" autoComplete="off" spellCheck={false} placeholder="/innovations" value={value ?? ''} onChange={(e) => set(e.target.value.trim() === '' ? '' : e.target.value)} />
        </Field>
      );
    case 'text':
    default:
      return (
        <Field label={field.label} htmlFor={id} required={field.required} hint={hintFor(field)} error={v.error} aside={<Counter value={value} max={field.max} />}>
          <input {...common} type="text" value={value ?? ''} onChange={(e) => set(e.target.value)} />
        </Field>
      );
  }
}

function AutoTextarea(props) {
  const [el, setEl] = useState(null);
  useEffect(() => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight + 2, 360)}px`;
  }, [el, props.value]);
  return <textarea ref={setEl} rows={3} {...props} />;
}
