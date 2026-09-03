import { Inbox } from 'lucide-react';
import { Link } from 'react-router-dom';

// Friendlier "nothing here yet" state used by resource lists and nested
// child managers: an icon, a short human sentence, and (optionally) a
// primary call-to-action instead of a plain bordered box of text.
export default function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  description,
  actionLabel,
  onAction,
  actionTo,
  compact = false,
}) {
  return (
    <div className={`empty-state${compact ? ' empty-state-compact' : ''}`}>
      <div className="empty-state-icon">
        <Icon size={compact ? 20 : 26} strokeWidth={1.6} aria-hidden="true" />
      </div>
      <p className="empty-state-title">{title}</p>
      {description && <p className="empty-state-desc">{description}</p>}
      {actionLabel && actionTo && (
        <Link to={actionTo} className="btn btn-primary btn-small">
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionTo && (
        <button type="button" className="btn btn-primary btn-small" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
