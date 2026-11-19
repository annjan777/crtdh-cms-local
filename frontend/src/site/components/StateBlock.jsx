// Shared loading / empty / error presentation so every page handles the
// three non-happy-path states consistently instead of crashing or showing
// nothing.

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="state-block" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ icon = '🗂️', title = 'Nothing here yet', message }) {
  return (
    <div className="state-block">
      <div className="state-block__icon" aria-hidden="true">
        {icon}
      </div>
      <strong>{title}</strong>
      {message ? <p className="mt-0">{message}</p> : null}
    </div>
  )
}

export function ErrorState({ title = "Couldn't load this content", message = 'Please try again later.' }) {
  return (
    <div className="state-block">
      <div className="state-block__icon" aria-hidden="true">
        ⚠️
      </div>
      <strong>{title}</strong>
      <p className="mt-0">{message}</p>
    </div>
  )
}

/**
 * Wraps the standard {loading, error, data} shape from useApi and renders
 * the right state, calling children(data) only once data is a non-empty
 * array/object.
 */
export function DataState({ loading, error, data, isEmpty, emptyProps, children }) {
  if (loading) return <Spinner />
  if (error) return <ErrorState />
  const empty = isEmpty ? isEmpty(data) : !data || (Array.isArray(data) && data.length === 0)
  if (empty) return <EmptyState {...emptyProps} />
  return children(data)
}
