// Pattern 1 — List / Index: past publishes; restore one as unpublished changes.
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { cms } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { useChanges } from '../shell/ChangesContext.jsx';
import { Banner, Dialog, ErrorPanel, Spinner, fmtDateTime } from '../ui/index.jsx';

export default function HistoryPage() {
  const { canPublish } = useAuth();
  const { refreshNow } = useChanges();
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [actionErr, setActionErr] = useState(null);

  const load = useCallback(() => {
    setError(null);
    cms.snapshots().then((r) => setList(r.snapshots || []), setError);
  }, []);
  useEffect(load, [load]);

  async function restore() {
    setBusy(true);
    setActionErr(null);
    try {
      await cms.restore(confirm.id);
      setDone(confirm);
      setConfirm(null);
      refreshNow();
    } catch (err) {
      setActionErr(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell crumb="Publish history">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Publish history</h1>
            <p className="lead">Every publish is kept as a version of the whole site. Restoring one copies its content back as unpublished changes, so you can check it before it goes live.</p>
          </header>
          {done ? (
            <Banner tone="ok" actions={<Link className="btn" to="/review">Review changes</Link>}>
              Version {done.id} from {fmtDateTime(done.published_at)} is restored as unpublished changes. The live site is unchanged until it is published.
            </Banner>
          ) : null}
          {error ? <ErrorPanel error={error} onRetry={load} title="The publish history couldn’t be loaded" /> : null}
          <div className="table-frame">
            <table className="data-table">
              <caption className="visually-hidden">Published versions, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">Version</th>
                  <th scope="col">Published</th>
                  <th scope="col">By</th>
                  <th scope="col">What changed</th>
                  <th scope="col">
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {!list && !error
                  ? [0, 1, 2].map((i) => (
                      <tr key={i} aria-hidden="true">
                        {[0, 1, 2, 3, 4].map((j) => (
                          <td key={j}>
                            <span className="skel skel-line" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : null}
                {list && !list.length ? (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-inline">
                        <p>
                          <strong>No publishes yet.</strong> The first publish creates version 1 here.
                        </p>
                        <Link className="btn" to="/review">
                          Review &amp; publish
                        </Link>
                      </div>
                    </td>
                  </tr>
                ) : null}
                {list?.map((s) => (
                  <tr key={s.id}>
                    <td className="num-cell">
                      {s.id}
                      {s.is_live ? <span className="tag tag-ok">Live now</span> : null}
                    </td>
                    <td>
                      <time dateTime={s.published_at}>{fmtDateTime(s.published_at)}</time>
                    </td>
                    <td>{s.published_by}</td>
                    <td className={s.note || s.summary ? undefined : 'muted'}>{s.note || s.summary || '—'}</td>
                    <td className="actions-cell">
                      {canPublish ? (
                        <button type="button" className="btn btn-small" onClick={() => setConfirm(s)}>
                          Restore
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!canPublish ? <p className="muted table-note">Publishers can restore an earlier version.</p> : null}
        </main>
      </div>
      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={confirm ? `Restore version ${confirm.id} from ${fmtDateTime(confirm.published_at)}?` : ''}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(null)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={restore} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              Restore version {confirm?.id}
            </button>
          </>
        }
      >
        <p>
          Its content, published by {confirm?.published_by}, is copied back into the CMS as unpublished changes. Edits made since then are replaced by it. Nothing changes on the live site until someone publishes.
        </p>
        {actionErr ? <Banner tone="danger">{actionErr.message} {actionErr.fix}</Banner> : null}
      </Dialog>
    </AppShell>
  );
}
