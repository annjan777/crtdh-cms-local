import { useState } from 'react';
import { Link, useMatch } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { useChanges } from './ChangesContext.jsx';
import RequestReviewDialog from '../review/RequestReviewDialog.jsx';
import { fmtTime } from '../ui/index.jsx';

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

export default function DraftBar() {
  const { canPublish } = useAuth();
  const { count, pageCount, changes, publish } = useChanges();
  const [asking, setAsking] = useState(false);
  const pageMatch = useMatch('/pages/:pageId');
  const onReview = useMatch('/review');
  const previewTo = `/pages/${pageMatch?.params.pageId || 'home'}?preview=1`;
  const running = publish && !['live', 'failed'].includes(publish.status);
  const waiting = changes?.review_request;

  let summary;
  if (running) summary = <span className="draft-text">Publishing · {publish.status === 'ready_for_upload' ? 'waiting for upload machine' : publish.step?.toLowerCase()}</span>;
  else if (!changes) summary = <span className="draft-text muted">Checking for changes…</span>;
  else if (count === 0) summary = <span className="draft-text muted">Everything is live</span>;
  else
    summary = (
      <span className="draft-text pending">
        <span className="dot" aria-hidden="true" />
        {plural(count, 'unpublished change')} on {plural(pageCount, 'page')}
      </span>
    );

  return (
    <div className="draft-bar" role="region" aria-label="Unpublished changes">
      <span aria-live="polite">{summary}</span>
      {waiting && !canPublish && count > 0 ? <span className="draft-text muted">Waiting for review since {fmtTime(waiting.at)}</span> : null}
      <Link className="btn" to={previewTo}>
        Preview
      </Link>
      {canPublish ? (
        onReview ? null : (
          <Link className="btn btn-primary" to="/review">
            Review &amp; publish
          </Link>
        )
      ) : onReview ? null : count > 0 && !waiting ? (
        <button type="button" className="btn btn-primary" onClick={() => setAsking(true)}>
          Request review
        </button>
      ) : (
        <Link className="btn" to="/review">
          See changes
        </Link>
      )}
      <RequestReviewDialog open={asking} onClose={() => setAsking(false)} />
    </div>
  );
}
