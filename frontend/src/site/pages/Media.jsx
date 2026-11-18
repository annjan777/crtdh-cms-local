import PageShell from '../components/PageShell.jsx'
import { Gallery, PageBanner } from '../components/Blocks.jsx'
import { formatDate, uniqueItems } from '../util.js'

/** Media (listing): events as galleries with an index, more photographs, press, newsletters. */
export default function Media({ data }) {
  const c = data.collections || {}
  const events = (c['media-events'] || []).filter((e) => (e.images || []).length)
  const gallery = c['gallery-images'] || []
  const coverage = c['media-coverage-links'] || []
  const documents = c.documents || []
  return (
    <PageShell data={data} className="media">
      <PageBanner
        title="Media and gallery"
        intro="Photographs from CRTDH events, health camps and outreach programmes, with press coverage and newsletters."
      >
        {events.length > 0 && (
          <nav className="jump" aria-label="Events on this page">
            <ul>
              {events.map((e) => (
                <li key={e.id}>
                  <a href={`#${e.slug}`}>{e.title}</a>
                </li>
              ))}
              {coverage.length > 0 && <li><a href="#press">Press coverage</a></li>}
              {documents.length > 0 && <li><a href="#newsletters">Newsletters</a></li>}
            </ul>
          </nav>
        )}
      </PageBanner>

      {events.map((e, i) => (
        <section key={e.id} id={e.slug} className={`section event${i % 2 ? ' section--surface' : ''}`} aria-labelledby={`event-${e.id}`}>
          <div className="wrap">
            <div className="section-head">
              <h2 id={`event-${e.id}`}>{e.title}</h2>
              {(e.event_date || e.description) && (
                <p>
                  {e.event_date && <time dateTime={e.event_date}>{formatDate(e.event_date)}</time>}
                  {e.event_date && e.description && '. '}
                  {e.description}
                </p>
              )}
            </div>
            <Gallery items={uniqueItems(e.images)} title={e.title} limit={6} />
          </div>
        </section>
      ))}

      {gallery.length > 0 && (
        <section className="section section--surface" aria-labelledby="more-photos">
          <div className="wrap">
            <div className="section-head">
              <h2 id="more-photos">More from CRTDH</h2>
            </div>
            <Gallery items={gallery} title="More from CRTDH" />
          </div>
        </section>
      )}

      {(coverage.length > 0 || documents.length > 0) && (
        <section className="section" aria-label="Press and newsletters">
          <div className="wrap two-col">
            {coverage.length > 0 && (
              <div id="press">
                <h2>Press coverage</h2>
                <ul className="rows mt-6">
                  {coverage.map((l) => (
                    <li key={l.id}>
                      <a href={l.url} className="rows__link" target="_blank" rel="noopener noreferrer">
                        <span>{pressLabel(l)}</span>
                        <span className="soft small">{host(l.url)}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {documents.length > 0 && (
              <div id="newsletters">
                <h2>Newsletters</h2>
                <ul className="rows mt-6">
                  {documents.map((d) => (
                    <li key={d.id}>
                      <a href={d.file} className="rows__link" download>
                        <span>{d.title}</span>
                        <span className="soft small">PDF</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}
    </PageShell>
  )
}

function host(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

// Several coverage rows use the URL as their title; show a readable headline from the slug instead.
function pressLabel(link) {
  const t = (link.title || '').trim()
  if (t && !/^https?:\/\//.test(t)) return t
  try {
    const u = new URL(link.url)
    const seg = u.pathname.split('/').filter(Boolean).reverse().find((s) => /[a-z]-[a-z]/i.test(s)) || ''
    const words = seg.replace(/\.[a-z]+$/i, '').replace(/-?(article)?\d{5,}.*$/i, '').split('-').filter(Boolean)
    if (words.length >= 3) {
      const s = words.join(' ')
      return s.charAt(0).toUpperCase() + s.slice(1)
    }
    return host(link.url)
  } catch {
    return t
  }
}
