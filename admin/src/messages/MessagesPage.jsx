// Pattern: Inbox (split pane on wide screens, list then detail on phones).
// Messages from the public contact form. Publishers and Admins only; the
// server stores them HTML-escaped, so they are decoded and shown as text.
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { messages as messagesApi } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { decodeEntities } from './decode.js';
import { Banner, Dialog, ErrorPanel, Spinner, fmtDateTime } from '../ui/index.jsx';

export default function MessagesPage() {
  const { canPublish } = useAuth();
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [actionErr, setActionErr] = useState(null);

  const load = useCallback(() => {
    setError(null);
    messagesApi.list().then(setList, setError);
  }, []);
  useEffect(() => {
    if (canPublish) load();
  }, [canPublish, load]);

  if (!canPublish)
    return (
      <AppShell crumb="Messages">
        <main id="main" className="page-main solo">
          <ErrorPanel title="Only Publishers and Admins can read messages" error={{ message: 'Messages from the contact form can include personal details.', fix: 'Ask a Publisher to pass on anything you need.' }} />
        </main>
      </AppShell>
    );

  const open = list?.find((m) => m.id === openId) || null;
  const name = (m) => decodeEntities(m.name) || 'No name given';

  async function remove() {
    setBusy(true);
    setActionErr(null);
    try {
      await messagesApi.remove(confirm.id);
      setList((l) => l.filter((m) => m.id !== confirm.id));
      setNotice(`The message from ${name(confirm)} was deleted.`);
      if (openId === confirm.id) setOpenId(null);
      setConfirm(null);
    } catch (err) {
      setActionErr(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell crumb="Messages">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Messages</h1>
            <p className="lead">Sent through the contact form on the website, newest first. Delete a message once it’s handled, or when someone asks for their details to be removed.</p>
          </header>
          {notice ? <Banner tone="ok">{notice}</Banner> : null}
          {error ? <ErrorPanel error={error} onRetry={load} title="Messages couldn’t be loaded" /> : null}
          {list && list.length === 0 ? (
            <div className="empty-section">
              <h2>No messages</h2>
              <p className="muted">New messages from the contact page appear here. An email also goes to the lab’s address.</p>
            </div>
          ) : null}
          {!list && !error ? <p className="muted" role="status"><Spinner /> Loading messages</p> : null}
          {list && list.length ? (
            <div className={`inbox${open ? ' has-open' : ''}`}>
              <ul className="inbox-list" aria-label="Messages">
                {list.map((m) => (
                  <li key={m.id}>
                    <button type="button" className="inbox-item" aria-current={m.id === openId ? 'true' : undefined} onClick={() => setOpenId(m.id)}>
                      <span className="inbox-from">{name(m)}</span>
                      <span className="inbox-date">{fmtDateTime(m.created_at)}</span>
                      <span className="inbox-snippet">{decodeEntities(m.message)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <section className="inbox-detail" aria-label="Message">
                {open ? (
                  <>
                    <button type="button" className="link-btn inbox-back" onClick={() => setOpenId(null)}>
                      ← All messages
                    </button>
                    <h2>{name(open)}</h2>
                    <dl className="facts">
                      <dt>Email</dt>
                      <dd>{open.email ? <a href={`mailto:${decodeEntities(open.email)}`}>{decodeEntities(open.email)}</a> : '—'}</dd>
                      <dt>Phone</dt>
                      <dd>{decodeEntities(open.phone) || '—'}</dd>
                      <dt>Received</dt>
                      <dd>{fmtDateTime(open.created_at)}</dd>
                    </dl>
                    <p className="message-body">{decodeEntities(open.message)}</p>
                    <div className="row-actions">
                      {open.email ? (
                        <a className="btn btn-primary" href={`mailto:${decodeEntities(open.email)}?subject=${encodeURIComponent('Your message to CRTDH')}`}>
                          Reply by email
                        </a>
                      ) : null}
                      <button type="button" className="btn btn-danger-text" onClick={() => setConfirm(open)}>
                        Delete message
                      </button>
                    </div>
                  </>
                ) : (
                  <p className="muted">Choose a message to read it.</p>
                )}
              </section>
            </div>
          ) : null}
        </main>
      </div>
      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={`Delete the message from ${confirm ? name(confirm) : ''}?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(null)}>
              Cancel
            </button>
            <button type="button" className="btn btn-danger" aria-busy={busy || undefined} onClick={remove}>
              {busy ? <Spinner /> : null}
              Delete message
            </button>
          </>
        }
      >
        {actionErr ? <Banner tone="danger">{actionErr.message} {actionErr.fix}</Banner> : null}
        <p>It’s removed from the editor for good and can’t be brought back. The copy in the lab’s email inbox isn’t affected.</p>
      </Dialog>
    </AppShell>
  );
}
