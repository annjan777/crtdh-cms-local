// Small shared UI pieces. Styling lives in styles/app.css.
import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';

export function Field({ label, htmlFor, hint, error, children, aside, required }) {
  return (
    <div className={`field${error ? ' has-error' : ''}`}>
      <div className="field-head">
        <label htmlFor={htmlFor}>
          {label}
          {required ? <span className="req" aria-hidden="true"> *</span> : null}
        </label>
        {aside ? <span className="field-aside">{aside}</span> : null}
      </div>
      {children}
      {error ? (
        <p className="field-error" id={`${htmlFor}-msg`} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="field-hint" id={`${htmlFor}-msg`}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Spinner({ label }) {
  return <span className="spinner" role={label ? 'status' : undefined} aria-label={label} />;
}

// Native <dialog>: focus is trapped by the browser while it is modal, Escape
// closes it, and focus returns to whatever opened it.
export function Dialog({ open, title, onClose, children, actions, size = 'sm', initialFocus = 'cancel', labelledBy }) {
  const ref = useRef(null);
  const trigger = useRef(null);
  const titleId = useId();
  useLayoutEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      trigger.current = document.activeElement;
      d.showModal();
      const target = d.querySelector(`[data-autofocus="${initialFocus}"]`) || d.querySelector('[data-autofocus]') || d.querySelector('button');
      target?.focus();
    } else if (!open && d.open) {
      d.close();
      trigger.current?.focus?.();
    }
  }, [open, initialFocus]);
  useEffect(() => {
    const d = ref.current;
    const onCancel = (e) => {
      e.preventDefault();
      onClose?.();
    };
    d?.addEventListener('cancel', onCancel);
    return () => d?.removeEventListener('cancel', onCancel);
  }, [onClose]);
  return (
    <dialog ref={ref} className={`dialog dialog-${size}`} aria-labelledby={labelledBy || titleId}>
      {open ? (
        <>
          <h2 id={titleId} className="dialog-title">
            {title}
          </h2>
          <div className="dialog-body">{children}</div>
          {actions ? <div className="dialog-actions">{actions}</div> : null}
        </>
      ) : null}
    </dialog>
  );
}

// Square icon button with a real tooltip on hover and keyboard focus.
export function IconButton({ label, shortcut, onClick, children, pressed, className = '', ...rest }) {
  const tipId = useId();
  return (
    <span className="tip-wrap">
      <button
        type="button"
        className={`icon-btn ${className}`}
        aria-label={label}
        aria-describedby={tipId}
        aria-pressed={pressed}
        onClick={onClick}
        {...rest}
      >
        {children}
      </button>
      <span role="tooltip" id={tipId} className="tip">
        {label}
        {shortcut ? <kbd>{shortcut}</kbd> : null}
      </span>
    </span>
  );
}

export function Banner({ tone = 'info', children, actions, role }) {
  return (
    <div className={`banner banner-${tone}`} role={role || (tone === 'danger' ? 'alert' : 'status')}>
      <div className="banner-text">{children}</div>
      {actions ? <div className="banner-actions">{actions}</div> : null}
    </div>
  );
}

export function CopyButton({ text, label = 'Copy error details', className = 'btn btn-quiet' }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className={className}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
        } catch {
          /* clipboard blocked: nothing else to do */
        }
        setDone(true);
        setTimeout(() => setDone(false), 1800);
      }}
    >
      {done ? 'Copied' : label}
    </button>
  );
}

// Error block for a failed load: what happened, the fix, and a way out.
export function ErrorPanel({ error, onRetry, title = 'This couldn’t be loaded' }) {
  return (
    <div className="error-panel" role="alert">
      <h2>{title}</h2>
      <p>
        {error?.message} {error?.fix}
      </p>
      <div className="row-actions">
        {onRetry ? (
          <button type="button" className="btn" onClick={onRetry}>
            Try again
          </button>
        ) : null}
        {error?.supportText ? <CopyButton text={error.supportText()} /> : null}
      </div>
    </div>
  );
}

export function useDelayed(flag, ms = 120) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!flag) {
      setShow(false);
      return undefined;
    }
    const t = setTimeout(() => setShow(true), ms);
    return () => clearTimeout(t);
  }, [flag, ms]);
  return show;
}

export const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
export const fmtDateTime = (iso) => (iso ? `${fmtDate(iso)}, ${fmtTime(iso)}` : '');

export function relTime(iso) {
  if (!iso) return '';
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const today = new Date().toDateString() === new Date(iso).toDateString();
  return today ? `today at ${fmtTime(iso)}` : fmtDateTime(iso);
}
