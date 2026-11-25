// Photo field, kept deliberately simple: the photo, a Replace button, and Save / Keep current when a new
// one is chosen. Size rule: hero rejects < min_width, others warn < 1200 px. The photo description for
// screen readers is filled in automatically (the section's own title, else the file name). Fields with a
// position_field (the home hero) also get a focus point: click or drag on the photo, and the phone and computer
// previews show exactly what the site keeps in view.
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

// The site's own default when no point has been chosen (Home.css: object-position: right center).
const SITE_DEFAULT = [100, 50];
const WORD = { left: 0, center: 50, right: 100, top: 0, bottom: 100 };

/** "30% 45%" | "30 45" | "right top" | "" -> [across, down] in percent. */
function parsePosition(value) {
  if (!value || value === 'center center') return SITE_DEFAULT;
  const pct = value.match(/^(\d{1,3}(?:\.\d)?)%? (\d{1,3}(?:\.\d)?)%?$/);
  if (pct) return [Math.min(100, +pct[1]), Math.min(100, +pct[2])];
  let [x, y] = [50, 50];
  for (const w of value.split(' ')) {
    if (w === 'left' || w === 'right') x = WORD[w];
    else if (w === 'top' || w === 'bottom') y = WORD[w];
  }
  return [x, y];
}

const clamp = (n) => Math.round(Math.min(100, Math.max(0, n)));

function FocusPicker({ url, value, onChange, id }) {
  const [draft, setDraft] = useState(null); // the point while dragging or just set, until the saved value catches up
  const box = useRef(null);
  const dragging = useRef(false);
  const saved = parsePosition(value);
  const point = draft || saved;
  const setPoint = setDraft;

  const save = (p) => {
    // Sent as two plain numbers ("30 45"); the CMS stores "30% 45%". A "%" in the request body was refused by
    // the campus network filter in front of the live server.
    onChange(`${p[0]} ${p[1]}`);
    setDraft(null);
  };
  const at = (e) => {
    const r = box.current.getBoundingClientRect();
    return [clamp(((e.clientX - r.left) / r.width) * 100), clamp(((e.clientY - r.top) / r.height) * 100)];
  };
  const css = `${point[0]}% ${point[1]}%`;

  return (
    <div className="focus-picker">
      <p className="field-label" id={`${id}-focus-label`}>Part of the photo to keep in view</p>
      <p className="field-hint">
        Click or drag on the photo. Phones show only a narrow upright slice, so put the dot on what matters most.
      </p>
      <div
        ref={box}
        className="focus-picker__photo"
        onPointerDown={(e) => {
          e.preventDefault();
          dragging.current = true;
          e.currentTarget.setPointerCapture?.(e.pointerId);
          setPoint(at(e));
        }}
        onPointerMove={(e) => dragging.current && setPoint(at(e))}
        onPointerUp={(e) => {
          if (!dragging.current) return;
          dragging.current = false;
          const p = at(e);
          setPoint(p);
          save(p);
        }}
      >
        <img src={url} alt="" draggable={false} />
        <button
          type="button"
          className="focus-picker__dot"
          style={{ left: `${point[0]}%`, top: `${point[1]}%` }}
          aria-labelledby={`${id}-focus-label`}
          aria-description={`${point[0]}% across, ${point[1]}% down. Arrow keys move it.`}
          onKeyDown={(e) => {
            const step = e.shiftKey ? 10 : 2;
            const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
            if (!d) return;
            e.preventDefault();
            const p = [clamp(point[0] + d[0]), clamp(point[1] + d[1])];
            setPoint(p);
            save(p);
          }}
        />
      </div>
      <div className="focus-picker__previews" aria-hidden="true">
        <figure>
          <div className="focus-preview focus-preview--phone">
            <img src={url} alt="" style={{ objectPosition: css }} />
          </div>
          <figcaption>Phone</figcaption>
        </figure>
        <figure>
          <div className="focus-preview focus-preview--wide">
            <img src={url} alt="" style={{ objectPosition: css }} />
          </div>
          <figcaption>Computer</figcaption>
        </figure>
      </div>
    </div>
  );
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
      {url && !pending && field.position_field ? (
        <FocusPicker
          url={url}
          id={id}
          value={record.values[field.position_field]}
          onChange={(v) => onChange({ [field.position_field]: v })}
        />
      ) : shown ? (
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
