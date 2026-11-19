import { useState } from 'react'
import PageShell from '../components/PageShell.jsx'
import SiteLink from '../link.jsx'
import { PAGES } from '../registry.js'
import { SEO } from '../seo.js'

const ENTRIES = PAGES.map((p) => ({ to: p.path, label: p.title, hint: SEO[p.id]?.description || '' }))

/** Designed 404: says what happened, searches the site's pages, keeps the site chrome. */
export default function NotFound({ data }) {
  const [q, setQ] = useState('')
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean)
  const hits = ENTRIES.filter((e) => terms.every((t) => `${e.label} ${e.hint}`.toLowerCase().includes(t)))
  return (
    <PageShell data={data} className="notfound">
      <section className="section">
        <div className="wrap grid12">
          <div className="notfound__text">
            <h1>This page is not on the site</h1>
            <p className="lead mt-6">The address may be mistyped, or the page moved when the site was rebuilt.</p>
            <div className="field mt-8">
              <label htmlFor="page-search">Search the site’s pages</label>
              <input
                id="page-search"
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="e.g. anemia, facilities, membership"
                autoComplete="off"
              />
            </div>
            <div className="actions">
              <SiteLink to="/" className="btn btn--primary">Go to the home page</SiteLink>
            </div>
          </div>
          <div className="notfound__links">
            <p className="soft small" aria-live="polite">
              {terms.length ? `${hits.length} ${hits.length === 1 ? 'page matches' : 'pages match'}` : 'All pages'}
            </p>
            <ul className="rows">
              {hits.map((e) => (
                <li key={e.to}>
                  <SiteLink to={e.to} className="rows__link rows__link--stack">
                    <span>{e.label}</span>
                    <span className="soft small">{e.hint}</span>
                  </SiteLink>
                </li>
              ))}
            </ul>
            {terms.length > 0 && hits.length === 0 && (
              <p className="mt-4">No page matches “{q}”. Try a shorter word, or <SiteLink to="/contact/">ask the centre</SiteLink>.</p>
            )}
          </div>
        </div>
      </section>
    </PageShell>
  )
}
