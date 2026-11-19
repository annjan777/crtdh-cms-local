// Pattern 1 — List / Index: every unpublished change, grouped by page, with
// who made it and through which channel, before → after, discard per change
// or per Claude session, and the site-wide publish with its live status.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { cms } from '../api/cms.js';
import AppShell, { PageNav } from '../shell/AppShell.jsx';
import { CANCELLABLE, TERMINAL, useChanges } from '../shell/ChangesContext.jsx';
import { Banner, CopyButton, Dialog, ErrorPanel, Spinner, fmtTime, relTime } from '../ui/index.jsx';
import { plain } from '../editor/validate.js';
import RequestReviewDialog from './RequestReviewDialog.jsx';

const KIND = { added: 'Added', changed: 'Changed', hidden: 'Hidden', removed: 'Deleted' };
const STEPS = [
  ['queued', 'Queued'],
  ['building', 'Building the site'],
  ['uploading', 'Uploading to the server'],
  ['live', 'Live'],
];

function show(v) {
  if (v === true) return 'On';
  if (v === false) return 'Off';
  const t = plain(v).trim();
  if (!t) return 'empty';
  if (/^(data:image|\/_media\/|\/api\/v1\/media\/|https?:\/\/.*\.(jpe?g|png|webp|avif)$)/i.test(String(v))) return 'a photo';
  return t.length > 140 ? `${t.slice(0, 137)}…` : t;
}

function Thumb({ v }) {
  return typeof v === 'string' && /^(data:image\/|\/_media\/|\/api\/v1\/media\/)/.test(v) ? <img className="diff-thumb" src={v} alt="" /> : null;
}

function ChangeRow({ change, onDiscard }) {
  const via = change.channel === 'claude' || change.channel === 'mcp' ? 'through Claude' : 'in the editor';
  return (
    <li className="change">
      <div className="change-head">
        <span className={`kind kind-${change.kind}`}>{KIND[change.kind]}</span>
        <h3 className="change-label">{change.label}</h3>
        <span className="change-section muted">{change.section}</span>
        <button type="button" className="btn btn-small" onClick={() => onDiscard(change)}>
          Discard
        </button>
      </div>
      <p className="change-meta">
        {change.author} {via}
        {change.at ? <> · <time dateTime={change.at}>{relTime(change.at)}</time></> : null}
      </p>
      {change.fields?.length ? (
        <dl className="diff">
          {change.fields.map((f) => (
            <div key={f.name} className="diff-row">
              <dt>{f.label || f.name}</dt>
              <dd>
                {change.kind !== 'added' ? (
                  <>
                    <del>
                      <Thumb v={f.before} />
                      {show(f.before)}
                    </del>
                    <span className="arrow" aria-label="changed to">→</span>
                  </>
                ) : null}
                <ins>
                  <Thumb v={f.after} />
                  {show(f.after)}
                </ins>
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </li>
  );
}

export function PublishStatus({ publish, onRetry, onCancel }) {
  const [cancelling, setCancelling] = useState(false);
  const [cancelErr, setCancelErr] = useState(null);
  if (!publish) return null;
  const { status } = publish;
  if (status === 'cancelled')
    return (
      <Banner tone="info">
        <strong>Publish cancelled.</strong> The live site is unchanged and your changes are still waiting here.
      </Banner>
    );
  if (publish.lost)
    return (
      <Banner tone="warn" actions={<button type="button" className="btn" onClick={() => window.location.reload()}>Reload the page</button>}>
        <strong>The publish status can’t be read right now.</strong> The publish may still finish. Reload the page in a minute to check; Publish history shows every version that went live.
      </Banner>
    );
  if (status === 'live')
    return (
      <Banner tone="ok">
        <strong>Live at {fmtTime(publish.live_at)}.</strong> The site now shows these changes.
      </Banner>
    );
  if (status === 'failed')
    return (
      <Banner tone="danger" actions={<button type="button" className="btn" onClick={onRetry}>Try again</button>}>
        <strong>Publish failed while {publish.step?.toLowerCase() || 'publishing'}.</strong> {publish.message} The site is unchanged.
      </Banner>
    );
  const waiting = status === 'ready_for_upload';
  const at = waiting ? 2 : Math.max(0, STEPS.findIndex(([s]) => s === status));
  return (
    <div className="publish-progress" role="status" aria-live="polite">
      <ol className="steps">
        {STEPS.map(([s, label], i) => (
          <li key={s} className={i < at ? 'done' : i === at ? 'current' : ''} aria-current={i === at ? 'step' : undefined}>
            {i === at && !waiting ? <Spinner /> : <span className="step-mark" aria-hidden="true" />}
            {label}
          </li>
        ))}
      </ol>
      {waiting ? (
        <p className="waiting">
          Waiting for upload machine{publish.agent_last_seen ? ` (last seen ${fmtTime(publish.agent_last_seen)})` : ''}. The site is built and will upload as soon as the campus PC checks in. The live site is unchanged until then.
        </p>
      ) : (
        <p className="muted">You can keep working; the live site changes only at the last step.</p>
      )}
      {onCancel && (publish.cancellable ?? CANCELLABLE.has(status)) ? (
        <div className="row-actions">
          <button
            type="button"
            className="btn"
            aria-busy={cancelling || undefined}
            onClick={async () => {
              setCancelling(true);
              setCancelErr(await onCancel());
              setCancelling(false);
            }}
          >
            {cancelling ? <Spinner /> : null}
            Cancel publish
          </button>
        </div>
      ) : null}
      {cancelErr ? (
        <p className="field-error" role="alert">
          {cancelErr.message} {cancelErr.fix}
        </p>
      ) : null}
    </div>
  );
}

export default function ReviewPage() {
  const { canPublish } = useAuth();
  const { changes, error, count, pageCount, refreshNow, setChanges, publish, startPublish, cancelPublish } = useChanges();
  const [discarding, setDiscarding] = useState(null); // {change} | {session}
  const [busy, setBusy] = useState(false);
  const [actionErr, setActionErr] = useState(null);
  const [guard, setGuard] = useState(null);
  const [asking, setAsking] = useState(false);
  const [publishErr, setPublishErr] = useState(null);
  const running = publish && !publish.lost && !TERMINAL.has(publish.status);

  const sessions = {};
  for (const p of changes?.pages || []) for (const c of p.changes) if (c.session_id) (sessions[c.session_id] ||= { id: c.session_id, author: c.author, n: 0 }).n += 1;

  async function doDiscard() {
    setBusy(true);
    setActionErr(null);
    try {
      const res = discarding.session ? await cms.discardSession(discarding.session.id) : await cms.discardItem(discarding.change.item_id);
      if (res?.pages) setChanges(res);
      setDiscarding(null);
      refreshNow();
    } catch (err) {
      setActionErr(err);
    } finally {
      setBusy(false);
    }
  }

  async function publishNow(confirmShrink = false) {
    setPublishErr(null);
    setGuard(null);
    const err = await startPublish(confirmShrink);
    if (err?.code === 'CMS_BUILD_GUARD') setGuard(err);
    else if (err) setPublishErr(err);
  }

  const shrink = guard?.details?.details?.[0];

  return (
    <AppShell crumb="Review & publish">
      <div className="editor is-wide page-layout">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Review &amp; publish</h1>
            <p className="lead">
              {count ? `${count} unpublished change${count === 1 ? '' : 's'} on ${pageCount} page${pageCount === 1 ? '' : 's'}. ` : ''}
              Publishing updates the whole site in one build. To keep a change out, discard it first: it goes back to what is live.
            </p>
          </header>

          <section className="publish-panel" aria-labelledby="publish-h">
            <h2 id="publish-h" className="visually-hidden">
              Publish
            </h2>
            <PublishStatus publish={publish} onRetry={() => publishNow()} onCancel={canPublish ? cancelPublish : null} />
            {publishErr ? (
              <Banner tone="danger" actions={<CopyButton text={publishErr.supportText?.() || ''} />}>
                {publishErr.message} {publishErr.fix}
              </Banner>
            ) : null}
            {canPublish ? (
              count > 0 && !running ? (
                <div className="publish-row">
                  <button type="button" className="btn btn-primary btn-large" onClick={() => publishNow()}>
                    Publish {count} change{count === 1 ? '' : 's'}
                  </button>
                  <p className="muted">Takes about a minute. The site stays as it is if anything fails.</p>
                </div>
              ) : null
            ) : count > 0 ? (
              <div className="publish-row">
                {changes?.review_request ? (
                  <p>
                    <strong>Waiting for review</strong> · requested by {changes.review_request.by} {relTime(changes.review_request.at)}. A Publisher will publish these changes.
                  </p>
                ) : (
                  <>
                    <button type="button" className="btn btn-primary btn-large" onClick={() => setAsking(true)}>
                      Request review
                    </button>
                    <p className="muted">Editors can’t publish. Publishers get an email with your note.</p>
                  </>
                )}
              </div>
            ) : null}
          </section>

          {Object.values(sessions).map((s) => (
            <Banner
              key={s.id}
              tone="info"
              actions={
                <button type="button" className="btn" onClick={() => setDiscarding({ session: s })}>
                  Discard all from this Claude session
                </button>
              }
            >
              Claude made {s.n} change{s.n === 1 ? '' : 's'} for {s.author} in one session. Check {s.n === 1 ? 'it' : 'them'} below before publishing.
            </Banner>
          ))}

          {error && !changes ? <ErrorPanel error={error} onRetry={refreshNow} title="The list of changes couldn’t be loaded" /> : null}
          {!changes && !error ? (
            <div className="change-group" aria-hidden="true">
              {[0, 1, 2].map((i) => (
                <div key={i} className="skel" style={{ height: 72, marginBottom: 12 }} />
              ))}
            </div>
          ) : null}
          {changes && count === 0 ? (
            <div className="empty-section">
              <h2>Nothing to publish</h2>
              <p>Every change is live. Edits made in the page editor, or by Claude, are listed here before they go live.</p>
              <Link className="btn btn-primary" to="/pages/home">
                Edit the Home page
              </Link>
            </div>
          ) : null}
          {changes?.pages.map((p) => (
            <section key={p.page} className="change-group" aria-labelledby={`g-${p.page}`}>
              <div className="group-head">
                <h2 id={`g-${p.page}`}>{p.title}</h2>
                <span className="muted">
                  {p.changes.length} change{p.changes.length === 1 ? '' : 's'}
                </span>
                <Link to={`/pages/${p.page}`} className="btn btn-small">
                  Open page
                </Link>
              </div>
              <ul className="change-list">
                {p.changes.map((c) => (
                  <ChangeRow key={c.item_id + c.kind} change={c} onDiscard={(change) => setDiscarding({ change })} />
                ))}
              </ul>
            </section>
          ))}
        </main>
      </div>

      <Dialog
        open={!!discarding}
        onClose={() => setDiscarding(null)}
        title={discarding?.session ? `Discard all ${discarding.session.n} changes from this Claude session?` : `Discard the change to “${discarding?.change?.label}”?`}
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setDiscarding(null)}>
              Cancel
            </button>
            <button type="button" className="btn btn-danger" onClick={doDiscard} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              {discarding?.session ? 'Discard session changes' : 'Discard change'}
            </button>
          </>
        }
      >
        <p>{discarding?.change?.kind === 'added' ? 'The new item is removed.' : 'It goes back to what is live on the site now.'} This can’t be undone.</p>
        {actionErr ? <Banner tone="danger">{actionErr.message} {actionErr.fix}</Banner> : null}
      </Dialog>

      <Dialog
        open={!!guard}
        onClose={() => setGuard(null)}
        title="Publish with a much shorter list?"
        actions={
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={() => setGuard(null)}>
              Cancel
            </button>
            <button type="button" className="btn btn-danger" onClick={() => publishNow(true)}>
              Publish anyway
            </button>
          </>
        }
      >
        <p>{guard?.message}</p>
        <p>
          {shrink ? `${shrink.before - shrink.after} items would disappear from the site. ` : ''}
          This usually means items were hidden or deleted by mistake. Nothing was uploaded; the site is unchanged.
        </p>
      </Dialog>
      <RequestReviewDialog open={asking} onClose={() => setAsking(false)} />
    </AppShell>
  );
}
