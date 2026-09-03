// Loading-skeleton primitives. Used in place of a bare spinner wherever we
// already know the shape of what's coming (a table of N columns, a row of
// stat cards) so the page doesn't flash empty before data arrives.
export function SkeletonBlock({ width, height = 14, radius = 6, style }) {
  return (
    <span
      className="skeleton-block"
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

export function SkeletonTable({ columns = 4, rows = 6 }) {
  return (
    <div className="skeleton-table" aria-hidden="true">
      <div className="skeleton-table-head" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0,1fr)) auto` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <SkeletonBlock key={i} width="60%" height={10} />
        ))}
        <SkeletonBlock width={60} height={10} />
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div
          className="skeleton-table-row"
          key={r}
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0,1fr)) auto` }}
        >
          {Array.from({ length: columns }).map((_, c) => (
            <SkeletonBlock key={c} width={c === 0 ? '70%' : '45%'} />
          ))}
          <SkeletonBlock width={64} height={26} radius={7} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonCards({ count = 4 }) {
  return (
    <div className="stat-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="stat-card stat-card-skeleton" key={i}>
          <SkeletonBlock width={34} height={34} radius={10} />
          <SkeletonBlock width="50%" height={22} style={{ marginTop: 14 }} />
          <SkeletonBlock width="70%" height={11} style={{ marginTop: 8 }} />
        </div>
      ))}
    </div>
  );
}
