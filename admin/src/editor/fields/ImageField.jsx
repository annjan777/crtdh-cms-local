// Photo field: current photo with its size, replace/upload with the size
// rule (hero rejects < min_width, others warn < 1200 px), required alt text,
// and, where the registry gives a position field, a focus point previewed at
// the desktop (16:9) and phone (4:5) crops side by side.
import { useEffect, useRef, useState } from 'react';
import { Banner, Field, Spinner } from '../../ui/index.jsx';
import { POSITIONS, checkImageSize, normalisePosition } from '../validate.js';

const SHOT_LIST = '/shot-list';

async function readDims(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) throw new Error('type');
  const bmp = await createImageBitmap(file);
  const out = { width: bmp.width, height: bmp.height };
  bmp.close?.();
  return out;
}

function Crops({ src, position, label }) {
  return (
    <div className="crops" aria-label={`${label} crops`}>
      <figure className="crop crop-169">
        <img src={src} alt="" style={{ objectPosition: position }} />
        <figcaption>Desktop · 16:9</figcaption>
      </figure>
      <figure className="crop crop-45">
        <img src={src} alt="" style={{ objectPosition: position }} />
        <figcaption>Phone · 4:5</figcaption>
      </figure>
    </div>
  );
}

export default function ImageField({ field, record, onChange, onUpload, id }) {
  const url = record.values[field.name];
  const media = record.media?.[field.name];
  const altName = field.alt_field;
  const alt = altName ? record.values[altName] ?? '' : '';
  const posName = field.position_field;
  const position = posName ? normalisePosition(record.values[posName]) : 'center center';
  const fileInput = useRef(null);
  const altInput = useRef(null);
  const [pending, setPending] = useState(null); // {file, url, width, height}
  const [pendingAlt, setPendingAlt] = useState('');
  const [problem, setProblem] = useState(null); // {level, message}
  const [altTouched, setAltTouched] = useState(false);
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
    setPendingAlt(alt);
    setAltTouched(false);
    setTimeout(() => altInput.current?.focus(), 0);
  }

  async function savePhoto() {
    if (altName && !pendingAlt.trim()) {
      setAltTouched(true);
      altInput.current?.focus();
      return;
    }
    setBusy(true);
    const err = await onUpload(field, pending.file, pendingAlt.trim());
    setBusy(false);
    if (err) {
      setProblem({ level: 'reject', message: `${err.message} ${err.fix || ''} Your current photo is kept.` });
      return;
    }
    setPending(null);
    if (problem?.level !== 'warn') setProblem(null);
  }

  const shown = pending?.url || url;
  const sizeNote = pending ? `${pending.file.name} · ${pending.width} × ${pending.height}` : media ? `${media.name} · ${media.width} × ${media.height}` : url ? url.split('/').pop().slice(0, 40) : null;
  const existingCheck = !pending && media ? checkImageSize(field, media.width) : null;
  const altMissing = altName && (pending ? altTouched && !pendingAlt.trim() : url && !String(alt).trim());
  const altId = `${id}-alt`;

  return (
    <fieldset className="field image-field">
      <legend>
        {field.label}
        {field.required ? <span className="req" aria-hidden="true"> *</span> : null}
      </legend>
      {shown ? (
        posName ? (
          <Crops src={shown} position={position} label={field.label} />
        ) : (
          <div className="image-preview">
            <img src={shown} alt="" />
          </div>
        )
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
      {sizeNote ? <p className="field-hint">{sizeNote}{pending ? ' · not saved yet' : ''}</p> : null}
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
      {altName ? (
        <Field
          label="Photo description"
          htmlFor={altId}
          required
          error={altMissing ? (pending ? 'Describe this photo before it can be saved.' : 'Add a description so people using screen readers know what this photo shows.') : null}
          hint="What the photo shows, e.g. “Health worker testing a blood sample at a village camp”."
        >
          <input
            ref={altInput}
            id={altId}
            type="text"
            maxLength={200}
            value={pending ? pendingAlt : alt}
            aria-invalid={altMissing || undefined}
            aria-describedby={`${altId}-msg`}
            onChange={(e) => (pending ? setPendingAlt(e.target.value) : onChange({ [altName]: e.target.value }))}
            onBlur={() => setAltTouched(true)}
          />
        </Field>
      ) : null}
      {posName && shown ? (
        <Field label="Focus point" htmlFor={`${id}-pos`} hint="The part of the photo that must stay in view when it is cropped.">
          <select id={`${id}-pos`} value={position} aria-describedby={`${id}-pos-msg`} onChange={(e) => onChange({ [posName]: e.target.value }, { immediate: true })}>
            {POSITIONS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </Field>
      ) : null}
      <div className="row-actions">
        {pending ? (
          <>
            <button type="button" className="btn btn-primary" onClick={savePhoto} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              {busy ? 'Uploading…' : 'Save photo'}
            </button>
            <button type="button" className="btn" onClick={() => { setPending(null); setProblem(null); }}>
              Keep current photo
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
