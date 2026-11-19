// Photo field, kept deliberately simple: the photo, a Replace button, and Save / Keep current when a new
// one is chosen. Size rule: hero rejects < min_width, others warn < 1200 px. The photo description for
// screen readers is filled in automatically (the section's own title, else the file name), and the crop
// stays centred, so editors only ever pick a photo.
import { useEffect, useRef, useState } from 'react';
import { Banner, Spinner } from '../../ui/index.jsx';
import { checkImageSize } from '../validate.js';

const SHOT_LIST = '/shot-list';

async function readDims(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) throw new Error('type');
  const bmp = await createImageBitmap(file);
  const out = { width: bmp.width, height: bmp.height };
  bmp.close?.();
  return out;
}

/** A short description for screen readers when the editor doesn't write one. */
export function autoDescription(record, file) {
  const v = record?.values || {};
  const own = ['title', 'heading', 'name', 'caption', 'text'].map((k) => v[k]).find((x) => typeof x === 'string' && x.trim());
  if (own) return own.trim().slice(0, 200);
  const base = (file?.name || '').replace(/\.[a-z0-9]+$/i, '').replace(/[_-]+/g, ' ').trim();
  return (base || 'Photo').slice(0, 200);
}

export default function ImageField({ field, record, onChange, onUpload, id }) {
  const url = record.values[field.name];
  const media = record.media?.[field.name];
  const fileInput = useRef(null);
  const [pending, setPending] = useState(null); // {file, url, width, height}
  const [problem, setProblem] = useState(null); // {level, message}
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  useEffect(() => () => pending && URL.revokeObjectURL(pending.url), [pending]);

  async function choose(file) {
    if (!file) return;
    setProblem(null);
    let d;
    try {
      d = await readDims(file);
    } catch {
      setProblem({ level: 'reject', message: 'This file isn’t a photo the site can use. Choose a JPEG, PNG or WebP photo. Your current photo is kept.' });
      return;
    }
    const check = checkImageSize(field, d.width);
    if (check.level === 'reject') {
      setProblem(check);
      return;
    }
    if (check.level === 'warn') setProblem(check);
    setPending({ file, url: URL.createObjectURL(file), ...d });
  }

  async function savePhoto() {
    setBusy(true);
    const err = await onUpload(field, pending.file, autoDescription(record, pending.file));
    setBusy(false);
    if (err) {
      setProblem({ level: 'reject', message: `${err.message} ${err.fix || ''} Your current photo is kept.` });
      return;
    }
    setPending(null);
    if (problem?.level !== 'warn') setProblem(null);
  }

  const shown = pending?.url || url;
  const existingCheck = !pending && media ? checkImageSize(field, media.width) : null;

  return (
    <fieldset className="field image-field">
      <legend>
        {field.label}
        {field.required ? <span className="req" aria-hidden="true"> *</span> : null}
      </legend>
      {shown ? (
        <div className="image-preview">
          <img src={shown} alt="" />
        </div>
      ) : (
        <div
          className={`drop-zone${drag ? ' is-over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            choose(e.dataTransfer.files?.[0]);
          }}
        >
          <p>Drop a photo here, or choose one.</p>
          <p className="field-hint">{field.min_width ? `At least ${field.min_width} px wide.` : `JPEG, PNG or WebP. ${field.warn_width || 1200} px wide or more looks best.`}</p>
        </div>
      )}
      {pending ? <p className="field-hint">New photo, not saved yet.</p> : null}
      {existingCheck && existingCheck.level !== 'ok' && !problem ? (
        <p className={existingCheck.level === 'reject' ? 'field-warn strong' : 'field-warn'}>
          {existingCheck.level === 'reject'
            ? `This photo is ${media.width} px wide; photos here need ${field.min_width} px. Replace it with a larger one.`
            : existingCheck.message}{' '}
          {field.min_width ? <a href={SHOT_LIST}>See the shot list</a> : null}
        </p>
      ) : null}
      {problem ? (
        <Banner tone={problem.level === 'reject' ? 'danger' : 'warn'}>
          {problem.message} {problem.level === 'reject' && field.min_width ? <a href={SHOT_LIST}>See the shot list</a> : null}
        </Banner>
      ) : null}
      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="visually-hidden"
        id={`${id}-file`}
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          choose(e.target.files?.[0]);
          e.target.value = '';
        }}
      />
      <div className="row-actions">
        {pending ? (
          <>
            <button type="button" className="btn btn-primary" onClick={savePhoto} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              {busy ? 'Uploading…' : 'Save photo'}
            </button>
            <button type="button" className="btn" onClick={() => { setPending(null); setProblem(null); }}>
              Cancel
            </button>
          </>
        ) : (
          <button type="button" className="btn" onClick={() => fileInput.current?.click()}>
            {url ? 'Replace photo' : 'Choose photo'}
          </button>
        )}
      </div>
      {busy ? <div className="progress" role="progressbar" aria-label="Uploading photo" /> : null}
    </fieldset>
  );
}
