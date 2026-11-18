// Pattern 1 — List / Index: CMS users, their roles, add and deactivate.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { users as usersApi } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { Banner, Dialog, ErrorPanel, Field, Spinner, fmtDate } from '../ui/index.jsx';

const ROLES = [
  ['editor', 'Editor', 'Edits drafts and requests review'],
  ['publisher', 'Publisher', 'Also publishes and restores versions'],
  ['admin', 'Admin', 'Also manages users'],
];

function AddUser({ open, onClose, onAdded }) {
  const [v, setV] = useState({ name: '', email: '', role: 'editor' });
  const [touched, setTouched] = useState({});
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const nameRef = useRef(null);
  const emailRef = useRef(null);
  const errs = {
    name: !v.name.trim() ? 'Enter the person’s full name.' : null,
    email: !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email) ? 'Enter an email like name@iitkgp.ac.in.' : null,
  };
  const shown = (k) => (touched[k] && errs[k]) || (err?.field === k ? err.message : null);
  const close = () => {
    setV({ name: '', email: '', role: 'editor' });
    setTouched({});
    setErr(null);
    onClose();
  };
  async function submit(e) {
    e.preventDefault();
    setTouched({ name: true, email: true });
    if (errs.name) return nameRef.current?.focus();
    if (errs.email) return emailRef.current?.focus();
    setBusy(true);
    setErr(null);
    try {
      const res = await usersApi.create({ name: v.name.trim(), email: v.email.trim(), role: v.role });
      onAdded(res.user);
      close();
    } catch (e2) {
      setErr(e2);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={open} onClose={close} size="drawer" title="Add a user" initialFocus="name">
      <form onSubmit={submit} noValidate className="drawer-form">
        <p className="dialog-lead">They get an email with a link to choose a password and set up two-step sign-in.</p>
        {err && !err.field ? <Banner tone="danger">{err.message} {err.fix}</Banner> : null}
        <Field label="Full name" htmlFor="u-name" error={shown('name')}>
          <input ref={nameRef} id="u-name" data-autofocus="name" autoComplete="off" value={v.name} aria-invalid={!!shown('name') || undefined} aria-describedby="u-name-msg" onChange={(e) => setV({ ...v, name: e.target.value })} onBlur={() => setTouched((t) => ({ ...t, name: true }))} onFocus={() => setTouched((t) => ({ ...t, name: false }))} />
        </Field>
        <Field label="Email" htmlFor="u-email" error={shown('email')}>
          <input ref={emailRef} id="u-email" type="email" autoComplete="off" placeholder="name@iitkgp.ac.in" value={v.email} aria-invalid={!!shown('email') || undefined} aria-describedby="u-email-msg" onChange={(e) => setV({ ...v, email: e.target.value })} onBlur={() => setTouched((t) => ({ ...t, email: true }))} onFocus={() => setTouched((t) => ({ ...t, email: false }))} />
        </Field>
        <fieldset className="field">
          <legend>Role</legend>
          {ROLES.map(([value, label, desc]) => (
            <label key={value} className="radio">
              <input type="radio" name="role" value={value} checked={v.role === value} onChange={() => setV({ ...v, role: value })} />
              <span>
                <strong>{label}</strong> <span className="muted">{desc}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={close}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" aria-busy={busy || undefined}>
            {busy ? <Spinner /> : null}
            Add and send invite
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export default function UsersPage() {
  const { user: me, isAdmin } = useAuth();
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [rowState, setRowState] = useState({});
  const [notice, setNotice] = useState(null);

  const load = useCallback(() => {
    setError(null);
    usersApi.list().then((r) => setList(r.users), setError);
  }, []);
  useEffect(load, [load]);

  async function update(u, values, msg) {
    setRowState((s) => ({ ...s, [u.id]: { busy: true } }));
    try {
      const res = await usersApi.update(u.id, values);
      setList((l) => l.map((x) => (x.id === u.id ? res.user : x)));
      setRowState((s) => ({ ...s, [u.id]: { ok: msg } }));
      setTimeout(() => setRowState((s) => ({ ...s, [u.id]: {} })), 2500);
    } catch (err) {
      setRowState((s) => ({ ...s, [u.id]: { err } }));
    }
  }

  if (!isAdmin)
    return (
      <AppShell crumb="Users">
        <main id="main" className="page-main solo">
          <ErrorPanel title="Only Admins can manage users" error={{ message: 'Your role doesn’t include user management.', fix: 'Ask an Admin to add or change a user.' }} />
        </main>
      </AppShell>
    );

  return (
    <AppShell crumb="Users">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head with-action">
            <div>
              <h1>Users</h1>
              <p className="lead">People who can sign in to the website editor. Deactivated users can’t sign in, and their Claude connections stop working.</p>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => setAdding(true)}>
              Add user
            </button>
          </header>
          {notice ? <Banner tone="ok">{notice}</Banner> : null}
          {error ? <ErrorPanel error={error} onRetry={load} title="The user list couldn’t be loaded" /> : null}
          <div className="table-frame">
            <table className="data-table">
              <caption className="visually-hidden">CMS users</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Role</th>
                  <th scope="col">Two-step sign-in</th>
                  <th scope="col">Last signed in</th>
                  <th scope="col">
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {!list && !error
                  ? [0, 1, 2, 3].map((i) => (
                      <tr key={i} aria-hidden="true">
                        {[0, 1, 2, 3, 4].map((j) => (
                          <td key={j}>
                            <span className="skel skel-line" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : null}
                {list?.map((u) => {
                  const st = rowState[u.id] || {};
                  const self = u.id === me.id;
                  return (
                    <tr key={u.id} className={u.is_active ? '' : 'is-inactive'}>
                      <td>
                        <span className="cell-main">{u.name}</span>
                        <span className="cell-sub">
                          {u.email}
                          {self ? ' · you' : ''}
                        </span>
                      </td>
                      <td>
                        <label className="visually-hidden" htmlFor={`role-${u.id}`}>
                          Role for {u.name}
                        </label>
                        <select id={`role-${u.id}`} className="select-compact" value={u.roles[0]} disabled={self || !u.is_active} onChange={(e) => update(u, { roles: [e.target.value] }, 'Role saved')}>
                          {ROLES.map(([v, l]) => (
                            <option key={v} value={v}>
                              {l}
                            </option>
                          ))}
                        </select>
                        <span className="cell-status" aria-live="polite">
                          {st.busy ? 'Saving…' : st.ok || (st.err ? `${st.err.message}` : '')}
                        </span>
                      </td>
                      <td>{u.mfa_enrolled ? 'Set up' : <span className="warn-text">Not set up yet</span>}</td>
                      <td>{u.last_login ? fmtDate(u.last_login) : <span className="muted">Never</span>}</td>
                      <td className="actions-cell">
                        {self ? null : u.is_active ? (
                          <button type="button" className="btn btn-small btn-danger-text" onClick={() => setConfirm(u)}>
                            Deactivate
                          </button>
                        ) : (
                          <button type="button" className="btn btn-small" onClick={() => update(u, { is_active: true }, 'Reactivated')}>
                            Reactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </main>
      </div>
      <AddUser
        open={adding}
        onClose={() => setAdding(false)}
        onAdded={(u) => {
          setList((l) => [...(l || []), u]);
          setNotice(`${u.name} was added as ${u.roles[0]}. An invite email is on its way to ${u.email}.`);
        }}
      />
      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={`Deactivate ${confirm?.name}?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={async () => {
                const u = confirm;
                setConfirm(null);
                await update(u, { is_active: false }, 'Deactivated');
              }}
            >
              Deactivate {confirm?.name?.split(' ')[0]}
            </button>
          </>
        }
      >
        <p>{confirm?.name} won’t be able to sign in, and any Claude connection they set up stops working within a minute. Their past edits stay in the history. You can reactivate them later.</p>
      </Dialog>
    </AppShell>
  );
}
