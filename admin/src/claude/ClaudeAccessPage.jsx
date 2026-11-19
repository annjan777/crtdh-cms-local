// Pattern: List / Index. Your Claude connections (docs/connect-claude.md "Disconnect Claude"), and for Admins,
// everyone's, each with a named confirmation before Disconnect. API: GET /cms/claude-access/,
// POST /cms/claude-access/revoke/ ({} = you, {user_id} = someone else, Admins only).
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { claudeAccess } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { Banner, CopyButton, Dialog, ErrorPanel, Spinner, fmtDateTime } from '../ui/index.jsx';

function Value({ label, value }) {
  return (
    <div className="connect-value">
      <span className="connect-value__label">{label}</span>
      <code className="connect-value__text">{value}</code>
      <CopyButton text={value} label={`Copy ${label.toLowerCase()}`} className="btn btn-small" />
    </div>
  );
}

/** Steps to add the connector in Claude (docs/connect-claude.md), with the values to paste. */
function ConnectSteps({ setup, isAdmin, issued, onIssue }) {
  const clientId = issued?.client_id || setup.client_id;
  return (
    <section aria-labelledby="connect-claude">
      <h2 id="connect-claude">Connect Claude</h2>
      <ol className="connect-steps">
        <li>
          In Claude, open <strong>Customize → Connectors</strong> and click <strong>Add custom connector</strong>.
          <span className="field-hint"> On a Team or Enterprise plan only an Owner can add it (Organization settings → Connectors); everyone else just clicks Connect.</span>
        </li>
        <li>
          Name it <strong>CRTDH CMS</strong> and paste this server URL:
          <Value label="Server URL" value={setup.server_url} />
        </li>
        <li>
          Open <strong>Advanced settings</strong> and paste the OAuth client ID and secret.
          {clientId ? <Value label="Client ID" value={clientId} /> : null}
          {issued ? (
            <>
              <Value label="Client secret" value={issued.client_secret} />
              <Banner tone="warn">Copy the secret now: it is shown only this once. Share it privately (not by email or chat). Anyone who already connected keeps working until their connection expires, then needs this new secret.</Banner>
            </>
          ) : isAdmin ? (
            <p className="field-hint">
              {clientId ? 'The secret is stored scrambled and can’t be shown again. ' : 'The Claude client isn’t set up yet. '}
              <br />
              <button type="button" className="btn btn-small" onClick={onIssue}>
                {clientId ? 'Create a new client secret' : 'Set up the Claude client'}
              </button>
            </p>
          ) : (
            <p className="field-hint">Ask an Admin for the client {clientId ? 'secret' : 'ID and secret'}.</p>
          )}
        </li>
        <li>Click <strong>Add</strong>, then <strong>Connect</strong>. Sign in to the CMS on the page that opens and click <strong>Allow</strong>.</li>
        <li>In a new chat, switch on CRTDH CMS under <strong>+ → Connectors</strong> and ask, for example, “Add Saturday’s eye camp to Media”. Claude saves drafts; a Publisher publishes them.</li>
      </ol>
    </section>
  );
}

function Connections({ rows }) {
  return (
    <ul className="plain-list">
      {rows.map((c, i) => (
        <li key={`${c.client}-${c.connected_at}-${i}`}>
          {c.client} · connected {fmtDateTime(c.connected_at)}
        </li>
      ))}
    </ul>
  );
}

export default function ClaudeAccessPage() {
  const { user, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [confirm, setConfirm] = useState(null); // {userId|null, name}
  const [busy, setBusy] = useState(false);
  const [actionErr, setActionErr] = useState(null);
  const [notice, setNotice] = useState(null);
  const [issued, setIssued] = useState(null); // {client_id, client_secret, server_url}, shown once
  const [askIssue, setAskIssue] = useState(false);
  const [issueErr, setIssueErr] = useState(null);

  async function issueSecret() {
    setBusy(true);
    setIssueErr(null);
    try {
      setIssued(await claudeAccess.newSecret());
      setAskIssue(false);
    } catch (err) {
      setIssueErr(err);
    } finally {
      setBusy(false);
    }
  }

  const load = useCallback(() => {
    setError(null);
    claudeAccess.get().then(setData, setError);
  }, []);
  useEffect(() => {
    claudeAccess.get().then(setData, setError);
  }, []);

  async function disconnect() {
    setBusy(true);
    setActionErr(null);
    try {
      await claudeAccess.revoke(confirm.userId);
      setNotice(confirm.userId == null ? 'Claude is disconnected from your account. It stops working on its next request.' : `Claude is disconnected for ${confirm.name}. It stops working on its next request.`);
      setConfirm(null);
      load();
    } catch (err) {
      setActionErr(err);
    } finally {
      setBusy(false);
    }
  }

  const others = (data?.users || []).filter((u) => u.user_id !== user.id);
  return (
    <AppShell crumb="Claude access">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Claude access</h1>
            <p className="lead">Claude can edit drafts for you once you connect it. It can’t publish. Disconnecting stops it on its next request.</p>
          </header>
          {notice ? <Banner tone="ok">{notice}</Banner> : null}
          {error ? <ErrorPanel error={error} onRetry={load} title="Claude access couldn’t be loaded" /> : null}
          {!data && !error ? <p className="muted" role="status"><Spinner /> Loading</p> : null}
          {data?.setup ? <ConnectSteps setup={data.setup} isAdmin={isAdmin} issued={issued} onIssue={() => setAskIssue(true)} /> : null}
          {data ? (
            <section aria-labelledby="own-claude">
              <h2 id="own-claude">Your account</h2>
              {data.connected ? (
                <>
                  <Connections rows={data.connections} />
                  <div className="row-actions">
                    <button type="button" className="btn btn-danger-text" onClick={() => setConfirm({ userId: null, name: 'you' })}>
                      Disconnect Claude
                    </button>
                  </div>
                </>
              ) : (
                <p className="muted">Claude isn’t connected to your account.</p>
              )}
            </section>
          ) : null}
          {data && isAdmin ? (
            <section aria-labelledby="all-claude">
              <h2 id="all-claude">Everyone’s connections</h2>
              {others.length ? (
                <div className="table-frame">
                  <table className="data-table stack">
                    <caption className="visually-hidden">Other people’s Claude connections</caption>
                    <thead>
                      <tr>
                        <th scope="col">Name</th>
                        <th scope="col">Connections</th>
                        <th scope="col">
                          <span className="visually-hidden">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {others.map((u) => (
                        <tr key={u.user_id}>
                          <td>
                            <span className="cell-main">{u.name}</span>
                            <span className="cell-sub">{u.username}</span>
                          </td>
                          <td data-label="Connections">
                            <Connections rows={u.connections} />
                          </td>
                          <td>
                            <button type="button" className="btn btn-danger-text" onClick={() => setConfirm({ userId: u.user_id, name: u.name })}>
                              Disconnect<span className="visually-hidden"> Claude for {u.name}</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">No one else has Claude connected.</p>
              )}
            </section>
          ) : null}
        </main>
      </div>
      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={confirm?.userId == null ? 'Disconnect Claude from your account?' : `Disconnect Claude for ${confirm?.name}?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setConfirm(null)}>
              Cancel
            </button>
            <button type="button" className="btn btn-danger" aria-busy={busy || undefined} onClick={disconnect}>
              {busy ? <Spinner /> : null}
              {confirm?.userId == null ? 'Disconnect Claude' : `Disconnect ${confirm?.name}`}
            </button>
          </>
        }
      >
        {actionErr ? <Banner tone="danger">{actionErr.message} {actionErr.fix}</Banner> : null}
        <p>
          {confirm?.userId == null ? 'Claude stops working with your account on its next request. Drafts it made stay as they are. To use it again, connect it again in Claude.' : `${confirm?.name}’s Claude stops working on its next request. Drafts it made stay as they are. They can connect it again later.`}
        </p>
      </Dialog>
      <Dialog
        open={askIssue}
        onClose={() => setAskIssue(false)}
        title={data?.setup?.client_id ? 'Create a new client secret?' : 'Set up the Claude client?'}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setAskIssue(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" aria-busy={busy || undefined} onClick={issueSecret}>
              {busy ? <Spinner /> : null}
              {data?.setup?.client_id ? 'Create new secret' : 'Set up'}
            </button>
          </>
        }
      >
        {issueErr ? <Banner tone="danger">{issueErr.message} {issueErr.fix}</Banner> : null}
        <p>
          {data?.setup?.client_id
            ? 'The old secret stops working for new connections. People already connected keep working until their connection expires (up to 30 days), then need the new secret in their connector.'
            : 'This creates the client Claude signs in with and shows its secret once.'}
        </p>
      </Dialog>
    </AppShell>
  );
}
