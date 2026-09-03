import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import ImageGrid from '../components/ImageGrid'
import { ExternalLink } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Media.css'

export default function Media() {
  const { data: events, loading, error } = useApi(() => fetchList('/media-events/'), [], [])
  const { data: coverageLinks, loading: coverageLoading } = useApi(
    () => fetchList('/media-coverage-links/'),
    [],
    [],
  )
  const { data: galleryImages, loading: galleryLoading } = useApi(
    () => fetchList('/gallery-images/'),
    [],
    [],
  )
  const location = useLocation()

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

  return (
    <div>
      <PageHero
        eyebrow="Media"
        title="Events, camps &amp; coverage"
        description="Photo galleries from CRTDH events, health camps and outreach programmes, plus press coverage."
      />

      <section className="section">
        <div className="container">
          <DataState
            loading={loading}
            error={error}
            data={events}
            emptyProps={{ title: 'Media galleries coming soon' }}
          >
            {(items) => (
              <div className="media-events">
                {items.map((event, i) => (
                  <Reveal as="section" className="media-event" id={event.slug} key={event.id} delay={Math.min(i, 4) * 0.05}>
                    <h2>{event.title}</h2>
                    <ImageGrid items={event.images} columns={4} aspect="wide" />
                  </Reveal>
                ))}
              </div>
            )}
          </DataState>
        </div>
      </section>

      {!galleryLoading && galleryImages && galleryImages.length > 0 && (
        <section className="section section--alt">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Gallery</span>
              <h2 className="section-title">More from CRTDH</h2>
            </Reveal>
            <ImageGrid items={galleryImages} columns={4} />
          </div>
        </section>
      )}

      {!coverageLoading && coverageLinks && coverageLinks.length > 0 && (
        <section className="section">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Press</span>
              <h2 className="section-title">Media coverage</h2>
            </Reveal>
            <ul className="coverage-list">
              {coverageLinks.map((link) => (
                <li key={link.id}>
                  <a href={link.url} target="_blank" rel="noreferrer" className="card coverage-list__item">
                    <span>{link.title}</span>
                    <span className="coverage-list__arrow" aria-hidden="true">
                      <ExternalLink size={16} aria-hidden="true" />
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  )
}
