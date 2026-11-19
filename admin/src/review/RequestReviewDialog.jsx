import { useState } from 'react';
import { cms } from '../api/cms.js';
import { useChanges } from '../shell/ChangesContext.jsx';
import { Banner, Dialog, Field, Spinner } from '../ui/index.jsx';

export default function RequestReviewDialog({ open, onClose }) {
  const { count, refreshNow } = useChanges();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(null);

  const close = () => {
    setError(null);
    setSent(null);
    setNote('');
    onClose();
  };

  async function send() {
    setBusy(true);
    setError(null);
    try {
      const res = await cms.requestReview(note.trim());
      // notified: names (mock) or a count (API). email_sent false: the request exists but nobody was emailed.
      setSent({ names: Array.isArray(res.notified) ? res.notified : [], emailed: res.email_sent !== false, message: res.message });
      refreshNow();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={close}
      title={sent ? 'Review requested' : 'Request a review'}
      initialFocus={sent ? 'done' : 'note'}
      actions={
        sent ? (
          <button type="button" className="btn btn-primary" data-autofocus="done" onClick={close}>
            Close
          </button>
        ) : (
          <>
            <button type="button" className="btn" data-autofocus="cancel" onClick={close}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={send} aria-busy={busy || undefined}>
              {busy ? <Spinner /> : null}
              Send request
            </button>
          </>
        )
      }
    >
      {sent && !sent.emailed ? (
        <>
          <Banner tone="warn">{sent.message || 'Review requested; the email to Publishers could not be sent.'}</Banner>
          <p>Your request is recorded and Publishers see it on Review &amp; publish, but nobody got an email. Tell a Publisher another way that your changes are ready.</p>
        </>
      ) : sent ? (
        <p>
          {sent.names.length ? `${sent.names.join(', ')} ${sent.names.length === 1 ? 'has' : 'have'} been emailed.` : 'Publishers have been emailed.'} The bar at the top shows “Waiting for review” until your changes are published.
        </p>
      ) : (
        <>
          <p className="dialog-lead">
            Publishers get an email asking them to check your {count} change{count === 1 ? '' : 's'} and publish them. Nothing goes live until they do.
          </p>
          {error ? (
            <Banner tone="danger">
              The email couldn’t be sent. {error.fix} Your changes are saved either way.
            </Banner>
          ) : null}
          <Field label="Note for the publisher" htmlFor="review-note" hint="Optional. For example, why the change is needed or when it should go live.">
            <textarea id="review-note" rows={3} value={note} data-autofocus="note" onChange={(e) => setNote(e.target.value)} aria-describedby="review-note-msg" />
          </Field>
        </>
      )}
    </Dialog>
  );
}
