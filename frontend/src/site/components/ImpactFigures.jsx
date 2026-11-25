import { usePageData } from '../api/data.jsx'
import './ImpactFigures.css'

/** Numbers an editor added for this page (CMS "impact-figures"), each with its source. Renders nothing without any. */
export default function ImpactFigures({ page, tone = 'light' }) {
  const data = usePageData()
  const rows = (data?.collections?.['impact-figures'] || []).filter((r) => r && r.page === page && r.is_published !== false)
  if (!rows.length) return null
  return (
    <section className={`figs figs--${tone}`} data-block={`${page}.figures`} aria-label="In numbers">
      <div className="container">
        <dl className="figs__row">
          {rows.map((r, k) => (
            <div className="figs__item" key={r.id} data-rv style={{ '--d': `${k * 90}ms` }}>
              <dt className="figs__label">{r.label}</dt>
              <dd className="figs__value">{r.value}</dd>
              {r.source && <dd className="figs__source">Source: {r.source}</dd>}
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
