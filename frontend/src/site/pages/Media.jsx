import { PageDataProvider } from '../api/data.jsx'
import { PlainLink } from '../link.jsx'
import { safeHref } from '../util.js'
import { useEffect, useRef, useState } from 'react'
import { useLocation } from '../router.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import PhotoMosaic from '../components/PhotoMosaic'
import { usePageMotion } from '../components/motion4.js'
import Lightbox from '../components/Lightbox'
import { ExternalLink, FileText } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import './Media.css'

// A press link whose CMS title is just its address reads as "publication — headline words from the address".
function linkLabel(link) {
  const t = (link.title || '').trim()
  if (!/^https?:\/\//i.test(t)) return t
  try {
    const u = new URL(t)
    const host = u.hostname.replace(/^www\./, '')
    const words = u.pathname.split('/').filter((p) => /[a-z]-[a-z]/i.test(p)).pop()
    return words ? `${host} — ${words.replace(/-\d+$/, '').replace(/-/g, ' ')}` : host
  } catch {
    return t
  }
}

function MediaView() {
  const { data: events, loading, error } = useApi(() => fetchList('/media-events/'), [], [])
  const { data: coverageLinks, loading: coverageLoading } = useApi(
    () => fetchList('/media-coverage-links/'),
    [],
    [],
  )
  const { data: documents } = useApi(() => fetchList('/documents/'), [], [])
  const { data: galleryImages, loading: galleryLoading } = useApi(
    () => fetchList('/gallery-images/'),
    [],
    [],
  )
  const location = useLocation()

  // Lightbox state
  const [lightboxState, setLightboxState] = useState({
    isOpen: false,
    images: [],
    currentIndex: 0
  })

  const openLightbox = (images, startIndex) => {
    setLightboxState({
      isOpen: true,
      images,
      currentIndex: startIndex
    })
  }

  const closeLightbox = () => setLightboxState(prev => ({ ...prev, isOpen: false }))
  
  const nextImage = () => setLightboxState(prev => ({ 
    ...prev, 
    currentIndex: (prev.currentIndex + 1) % prev.images.length 
  }))
  
  const prevImage = () => setLightboxState(prev => ({ 
    ...prev, 
    currentIndex: (prev.currentIndex - 1 + prev.images.length) % prev.images.length 
  }))

  // Deep links like /media#pathologyandeyeclinic must keep working: once the
  // event sections have rendered, scroll the matching anchor into view.
  useEffect(() => {
    if (!location.hash || loading) return
    const id = decodeURIComponent(location.hash.replace('#', ''))
    const el = document.getElementById(id)
    if (el) {
      // Defer to next paint so layout has settled.
      requestAnimationFrame(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    }
  }, [location.hash, loading])

  const ref = useRef(null)
  usePageMotion(ref, [events, galleryImages, coverageLinks, documents])
  const withPhotos = (events || []).filter((e) => e.images?.length)
  const cats = [...new Set(withPhotos.map((e) => (e.category || '').trim()).filter(Boolean))]
  const filters = [
    { id: 'all', label: 'All' },
    ...(cats.length > 1 ? cats.map((c) => ({ id: `cat:${c}`, label: c })) : [{ id: 'events', label: 'Events' }]),
    coverageLinks?.length ? { id: 'press', label: 'Press' } : null,
    documents?.length ? { id: 'newsletters', label: 'Newsletters' } : null,
  ].filter(Boolean)
  const [filter, setFilter] = useState('all')
  const show = (kind) => filter === 'all' || filter === kind || (kind === 'events' && filter.startsWith('cat:'))
  const shownEvents = filter.startsWith('cat:') ? withPhotos.filter((e) => `cat:${(e.category || '').trim()}` === filter) : withPhotos
  const [featured, ...rest] = shownEvents
  const side = rest.slice(0, 2)
  const more = rest.slice(2)
  const fmt = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : null)

  const Strip = ({ event }) => (
    <div className="news-strip" role="group" aria-label={`${event.title}: photos`}>
      {event.images.slice(0, 5).map((im, k) => (
        <button type="button" key={im.id} className="news-strip__btn zoom" onClick={() => openLightbox(event.images, k)}>
          <img src={im.image} alt={im.caption || ''} loading="lazy" />
          {k === 4 && event.images.length > 5 && <span className="news-strip__more" aria-hidden="true">+{event.images.length - 5}</span>}
          <span className="visually-hidden">Open photo {k + 1} of {event.images.length}</span>
        </button>
      ))}
    </div>
  )
  const Meta = ({ event }) => (
    <p className="news-meta">
      {event.category && <span>{event.category}</span>}
      {event.event_date && <time dateTime={event.event_date}>{fmt(event.event_date)}</time>}
      <span>{event.images.length} photos</span>
    </p>
  )

  return (
    <div ref={ref}>
      <PageHero
        page="media"
        eyebrow="Media"
        title="News &amp; updates"
        description="Photo galleries from CRTDH events, health camps and outreach programmes, plus press coverage."
        image={galleryImages?.[0]?.image}
      />

      {filters.length > 2 && (
        <div className="news-filter" role="toolbar" aria-label="Show">
          <div className="container news-filter__row">
            {filters.map((f) => (
              <button type="button" key={f.id} aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>{f.label}</button>
            ))}
          </div>
        </div>
      )}

      {show('events') && (
        <section data-block="media.events" className="news-events">
          <div className="container">
            <DataState loading={loading} error={error} data={events} emptyProps={{ title: 'Media galleries coming soon' }}>
              {() => featured && (
                <>
                  <div className="news-lead">
                    <article className="news-feature" id={featured.slug}>
                      <button type="button" className="news-feature__img zoom" onClick={() => openLightbox(featured.images, 0)} data-rv="mask">
                        <img src={featured.images[0].image} alt={featured.images[0].caption || ''} />
                        <span className="visually-hidden">Open the photos of {featured.title}</span>
                      </button>
                      <div className="news-feature__copy">
                        <Meta event={featured} />
                        <h2 className="news-feature__title">{featured.title}</h2>
                        {featured.description && <p className="news-desc">{featured.description}</p>}
                        <Strip event={featured} />
                      </div>
                    </article>
                    <div className="news-side">
                      {side.map((ev, k) => (
                        <article className="news-side__item" id={ev.slug} key={ev.id} style={{ '--d': `${k * 120}ms` }}>
                          <button type="button" className="news-side__img zoom" onClick={() => openLightbox(ev.images, 0)}>
                            <img src={ev.images[0].image} alt="" loading="lazy" />
                            <span className="visually-hidden">Open the photos of {ev.title}</span>
                          </button>
                          <div>
                            <Meta event={ev} />
                            <h2 className="news-side__title">{ev.title}</h2>
                            {ev.description && <p className="news-desc">{ev.description}</p>}
                            <Strip event={ev} />
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                  {more.length > 0 && (
                    <ol className="news-list">
                      {more.map((ev) => (
                        <li className="news-row" id={ev.slug} key={ev.id}>
                          <button type="button" className="news-row__img zoom" onClick={() => openLightbox(ev.images, 0)}>
                            <img src={ev.images[0].image} alt="" loading="lazy" />
                            <span className="visually-hidden">Open the photos of {ev.title}</span>
                          </button>
                          <div className="news-row__copy">
                            <Meta event={ev} />
                            <h2 className="news-row__title">{ev.title}</h2>
                            {ev.description && <p className="news-desc">{ev.description}</p>}
                          </div>
                          <Strip event={ev} />
                        </li>
                      ))}
                    </ol>
                  )}
                </>
              )}
            </DataState>
          </div>
        </section>
      )}

      {show('events') && !galleryLoading && galleryImages && galleryImages.length > 0 && (
        <section data-block="media.gallery" className="news-more">
          <div className="container">
            <div className="news-sec-head">
              <h2 className="section-title">More from CRTDH</h2>
            </div>
            <PhotoMosaic items={galleryImages} label="More from CRTDH" />
          </div>
        </section>
      )}

      {(show('press') || show('newsletters')) && (
        <section className="news-docs">
          <div className="container news-docs__grid">
            {show('press') && !coverageLoading && coverageLinks && coverageLinks.length > 0 && (
              <div data-block="media.coverage">
                <div className="news-sec-head">
                  <h2 className="section-title">Media coverage</h2>
                </div>
                <ul className="news-links">
                  {coverageLinks.map((link, k) => (
                    <li key={link.id} style={{ '--d': `${k * 50}ms` }}>
                      <a href={safeHref(link.url)} target="_blank" rel="noreferrer">
                        <span>{linkLabel(link)}</span>
                        <ExternalLink size={16} aria-hidden="true" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {show('newsletters') && documents.length > 0 && (
              <div data-block="media.documents" id="newsletters">
                <div className="news-sec-head">
                  <h2 className="section-title">Newsletters &amp; documents</h2>
                </div>
                <ul className="news-links">
                  {documents.map((doc, k) => (
                    <li key={doc.id} style={{ '--d': `${k * 50}ms` }}>
                      <PlainLink href={doc.file}>
                        <span>{doc.title}</span>
                        <FileText size={16} aria-hidden="true" />
                      </PlainLink>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {lightboxState.isOpen && (
        <Lightbox
          images={lightboxState.images}
          currentIndex={lightboxState.currentIndex}
          onClose={closeLightbox}
          onNext={nextImage}
          onPrev={prevImage}
        />
      )}
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Media({ data }) {
  return (
    <PageDataProvider data={data}>
      <MediaView />
    </PageDataProvider>
  )
}
