// Pattern: Settings. Download a backup of the CMS (content, or content + photos) and upload one to roll back.
// Admins only. An upload restores as unpublished changes, so nothing goes live until it is published.
// API: GET /cms/backup/[?photos=1] (zip download), POST /cms/backup/restore/ (multipart: file).
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { API_BASE } from '../api/client.js';
import { backups } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { Banner, Dialog, ErrorPanel, Spinner, fmtDateTime } from '../ui/index.jsx';

const MB = 1024 * 1024;
// Cloudflare's free plan refuses request bodies over 100 MB before they reach the CMS.
const CLOUDFLARE_LIMIT = 100 * MB;

export default function BackupPage() {
  const { isAdmin } = useAuth();
  const input = useRef(null);
  const [file, setFile] = useState(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);

  function choose(f) {
    setError(null);
    setDone(null);
    if (!f) return;
    if (!/\.zip$/i.test(f.name)) {
      setError({ message: 'Choose a backup file: it ends in .zip and starts with crtdh-backup.', fix: '' });
      return;
    }
    setFile(f);
    setConfirm(true);
  }

  async function restore() {
    setBusy(true);
    setError(null);
    try {
      setDone(await backups.restore(file));
      setConfirm(false);
      setFile(null);
    } catch (err) {
      setError(err);
      setConfirm(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell crumb="Backup">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Backup</h1>
            <p className="lead">Keep a copy of the website’s content off this server, and bring it back if something goes wrong.</p>
          </header>
          {!isAdmin ? (
            <Banner tone="info">Only an Admin can download or upload a backup.</Banner>
          ) : (
            <>
              <section aria-labelledby="download-title">
                <h2 id="download-title">Download a backup</h2>
                <p>Do this after big changes, and keep the file somewhere other than this server (your computer, Drive or email).</p>
                <div className="row-actions">
                  <a className="btn btn-primary" href={`${API_BASE}/cms/backup/`} download>
                    Download content
                  </a>
                  <a className="btn" href={`${API_BASE}/cms/backup/?photos=1`} download>
                    Download content + photos
                  </a>
                </div>
                <p className="field-hint">
                  <strong>Content</strong> is small: page text, settings and lists. Use it to undo bad edits while the photos are still on the server.{' '}
                  <strong>Content + photos</strong> is large (every photo) and is what you need if the server itself is lost.
                </p>
              </section>

              <section aria-labelledby="upload-title">
                <h2 id="upload-title">Upload a backup to roll back</h2>
                <p>
                  The backup comes back as <strong>unpublished changes</strong>. You can check them on{' '}
                  <Link to="/review">Review &amp; publish</Link>, discard any you don’t want, and nothing reaches the live site until you publish.
                </p>
                {done ? (
                  <Banner tone="ok">
                    Backup from {done.backup_created_at ? fmtDateTime(done.backup_created_at) : 'the file'} restored: {done.restored} change{done.restored === 1 ? '' : 's'}
                    {done.photos_written ? `, ${done.photos_written} photo${done.photos_written === 1 ? '' : 's'} put back` : ''}. <Link to="/review">Review &amp; publish</Link> to make it live.
                  </Banner>
                ) : null}
                {error ? <ErrorPanel error={error} title="The backup couldn’t be restored. Nothing was changed." /> : null}
                <input
                  ref={input}
                  type="file"
                  accept=".zip,application/zip"
                  className="visually-hidden"
                  id="backup-file"
                  tabIndex={-1}
                  aria-hidden="true"
                  onChange={(e) => {
                    choose(e.target.files?.[0]);
                    e.target.value = '';
                  }}
                />
                <div className="row-actions">
                  <button type="button" className="btn" onClick={() => input.current?.click()} disabled={busy}>
                    Choose backup file…
                  </button>
                </div>
                <p className="field-hint">
                  A full backup larger than 100 MB can’t pass through Cloudflare: upload it from the campus network, or use a content backup.
                </p>
              </section>
            </>
          )}
        </main>
      </div>
      <Dialog
        open={confirm && !!file}
        onClose={() => !busy && setConfirm(false)}
        title="Restore this backup?"
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(false)} disabled={busy}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={restore} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              {busy ? 'Restoring…' : 'Restore as unpublished changes'}
            </button>
          </>
        }
      >
        <p>
          <strong>{file?.name}</strong> ({file ? Math.max(1, Math.round(file.size / MB)) : 0} MB)
        </p>
        <p>The CMS content is set back to this backup as unpublished changes. Any unpublished edits made since are replaced. The live site doesn’t change until someone publishes.</p>
        <p>Not sure? <a href={`${API_BASE}/cms/backup/`} download>Download a backup of the current content</a> first.</p>
        {file && file.size > CLOUDFLARE_LIMIT ? (
          <Banner tone="warn">This file is over 100 MB. Through Cloudflare the upload will be refused; use the campus network.</Banner>
        ) : null}
      </Dialog>
    </AppShell>
  );
}
