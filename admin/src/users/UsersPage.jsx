// Pattern 1 — List / Index: CMS users, their roles, add and deactivate.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { ROLE_LABEL, topRole } from '../auth/roles.js';
import { users as usersApi } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { Banner, Dialog, ErrorPanel, Field, Spinner, fmtDate } from '../ui/index.jsx';

const ROLES = [
  ['editor', 'Editor', 'Edits drafts and requests review'],
  ['publisher', 'Publisher', 'Also publishes and restores versions'],
  ['admin', 'Admin', 'Also manages users'],
];

const EMPTY = { name: '', username: '', email: '', role: 'editor' };
const suggestUsername = (name) => name.trim().toLowerCase().split(/\s+/)[0]?.replace(/[^a-z0-9._-]/g, '') || '';

function AddUser({ open, onClose, onAdded }) {
  const [v, setV] = useState(EMPTY);
  const [userEdited, setUserEdited] = useState(false);
  const [touched, setTouched] = useState({});
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const refs = { name: useRef(null), username: useRef(null), email: useRef(null) };
  const errs = {
    name: !v.name.trim() ? 'Enter the person’s full name.' : null,
    username: !/^[A-Za-z0-9._-]{3,64}$/.test(v.username) ? 'Use 3 or more letters or digits (dots, dashes and underscores are fine).' : null,
    email: !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email) ? 'Enter an email like name@iitkgp.ac.in.' : null,
  };
  const shown = (k) => (touched[k] && errs[k]) || (err?.field === k ? err.message : null);
  const set = (k, value) => {
    setV((cur) => ({ ...cur, [k]: value, ...(k === 'name' && !userEdited ? { username: suggestUsername(value) } : {}) }));
    setTouched((t) => ({ ...t, [k]: false }));
    if (err?.field === k) setErr(null);
  };
  const close = () => {
    setV(EMPTY);
    setUserEdited(false);
    setTouched({});
    setErr(null);
    onClose();
  };
  async function submit(e) {
    e.preventDefault();
    setTouched({ name: true, username: true, email: true });
    const first = ['name', 'username', 'email'].find((k) => errs[k]);
    if (first) return refs[first].current?.focus();
    setBusy(true);
    setErr(null);
    const [first_name, ...rest] = v.name.trim().split(/\s+/);
    try {
      const res = await usersApi.create({ username: v.username, email: v.email.trim(), first_name, last_name: rest.join(' '), role: v.role });
      const { temporary_password, ...user } = res;
      onAdded(user, temporary_password);
      close();
    } catch (e2) {
      setErr(e2);
      if (e2.field && refs[e2.field]) refs[e2.field].current?.focus();
    } finally {
      setBusy(false);
    }
  }
  const input = (k, label, props = {}) => (
    <Field label={label} htmlFor={`u-${k}`} error={shown(k)}>
      <input ref={refs[k]} id={`u-${k}`} data-autofocus={k === 'name' ? 'name' : undefined} autoComplete="off" value={v[k]} aria-invalid={!!shown(k) || undefined} aria-describedby={`u-${k}-msg`} onChange={(e) => set(k, e.target.value)} onBlur={() => setTouched((t) => ({ ...t, [k]: true }))} {...props} />
    </Field>
  );
  return (
    <Dialog open={open} onClose={close} size="drawer" title="Add a user" initialFocus="name">
      <form onSubmit={submit} noValidate className="drawer-form">
        <p className="dialog-lead">You’ll get a temporary password to pass on. At first sign-in they set up two-step sign-in and choose their own password.</p>
        {err && !err.field ? <Banner tone="danger">{err.message} {err.fix}</Banner> : null}
        {input('name', 'Full name')}
        {input('username', 'Username', {
          spellCheck: false,
          onChange: (e) => {
            setUserEdited(true);
            set('username', e.target.value);
          },
        })}
        {input('email', 'Email', { type: 'email', placeholder: 'name@iitkgp.ac.in' })}
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
            Add user
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
  const [temp, setTemp] = useState(null);
  const [resetting, setResetting] = useState(null);

  const load = useCallback(() => {
    setError(null);
    usersApi.list().then(setList, setError);
  }, []);
  useEffect(load, [load]);

  async function update(u, call, msg, reason = null) {
    setRowState((s) => ({ ...s, [u.id]: { busy: true } }));
    try {
      const { temporary_password, ...res } = await call();
      setList((l) => l.map((x) => (x.id === u.id ? res : x)));
      // reset-mfa and reset-password replace the password; show the new one once.
      if (temporary_password) setTemp({ user: res, password: temporary_password, reason });
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
            <table className="data-table stack">
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
                      <td data-label="Role">
                        <label className="visually-hidden" htmlFor={`role-${u.id}`}>
                          Role for {u.name}
                        </label>
                        {u.is_active ? (
                          <select id={`role-${u.id}`} className="select-compact" value={topRole(u.roles) || 'editor'} disabled={self} onChange={(e) => { const role = e.target.value; update(u, () => usersApi.setRole(u.id, role), 'Role saved'); }}>
                            {ROLES.map(([v, l]) => (
                              <option key={v} value={v}>
                                {l}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="muted">Deactivated</span>
                        )}
                        <span className="cell-status" aria-live="polite">
                          {st.busy ? 'Saving…' : st.ok || (st.err ? `${st.err.message}` : '')}
                        </span>
                      </td>
                      <td data-label="Two-step sign-in">
                        {u.mfa_enrolled ? 'Set up' : <span className="warn-text">Not set up yet</span>}
                        {u.mfa_enrolled && u.is_active && !self ? (
                          <button type="button" className="link-btn cell-action" onClick={() => setResetting({ user: u, kind: 'mfa' })}>
                            Reset<span className="visually-hidden"> two-step sign-in for {u.name}</span>
                          </button>
                        ) : null}
                      </td>
                      <td data-label="Last signed in">{u.last_login ? fmtDate(u.last_login) : <span className="muted">Never</span>}</td>
                      <td className="actions-cell">
                        {self || !u.is_active ? null : (
                          <>
                            <button type="button" className="btn btn-small" onClick={() => setResetting({ user: u, kind: 'password' })}>
                              Reset password<span className="visually-hidden"> for {u.name}</span>
                            </button>
                            <button type="button" className="btn btn-small btn-danger-text" onClick={() => setConfirm(u)}>
                              Deactivate
                            </button>
                          </>
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
        onAdded={(u, password) => {
          setList((l) => [...(l || []), u]);
          setNotice(`${u.name} was added as ${ROLE_LABEL[topRole(u.roles)] || 'Editor'}.`);
          if (password) setTemp({ user: u, password });
        }}
      />
      <Dialog
        open={!!temp}
        onClose={() => setTemp(null)}
        title={`Temporary password for ${temp?.user.name}`}
        actions={
          <button type="button" className="btn btn-primary" data-autofocus="done" onClick={() => setTemp(null)}>
            Done
          </button>
        }
      >
        <p>
          {temp?.reason === 'mfa'
            ? `Two-step sign-in was reset and ${temp?.user.name}’s old password no longer works. `
            : temp?.reason === 'password'
              ? `${temp?.user.name}’s old password no longer works. `
              : ''}
          Give this temporary password to {temp?.user.name?.split(' ')[0]} in person or by phone, with the username <strong>{temp?.user.username}</strong>. It’s shown only once. At their next sign-in they {temp?.reason === 'password' ? '' : 'set up two-step sign-in and '}choose their own password.
        </p>
        <p className="temp-password">
          <code>{temp?.password}</code>
          <button type="button" className="btn btn-small" onClick={() => navigator.clipboard?.writeText(temp?.password || '')}>
            Copy
          </button>
        </p>
      </Dialog>
      <Dialog
        open={!!resetting}
        onClose={() => setResetting(null)}
        title={resetting?.kind === 'password' ? `Reset the password for ${resetting?.user.name}?` : `Reset two-step sign-in for ${resetting?.user.name}?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setResetting(null)}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={async () => {
                const { user: u, kind } = resetting;
                setResetting(null);
                if (kind === 'password') await update(u, () => usersApi.resetPassword(u.id), 'Password reset', 'password');
                else await update(u, () => usersApi.resetMfa(u.id), 'Two-step sign-in reset', 'mfa');
              }}
            >
              {resetting?.kind === 'password' ? 'Reset password' : 'Reset two-step sign-in'}
            </button>
          </>
        }
      >
        {resetting?.kind === 'password' ? (
          <p>Use this when {resetting?.user.name} has forgotten their password. Their current password stops working at once and you get a temporary one to pass on. Their two-step sign-in stays as it is.</p>
        ) : (
          <p>Use this when {resetting?.user.name} has lost their phone. Their authenticator app, recovery codes and current password stop working at once. You get a temporary password to pass on, and they set up two-step sign-in again at their next sign-in.</p>
        )}
      </Dialog>
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
                await update(u, () => usersApi.deactivate(u.id), 'Deactivated');
              }}
            >
              Deactivate {confirm?.name?.split(' ')[0]}
            </button>
          </>
        }
      >
        <p>{confirm?.name} won’t be able to sign in, and any Claude connection they set up stops working within a minute. Their past edits stay in the history. To undo this, ask the server administrator.</p>
      </Dialog>
    </AppShell>
  );
}
