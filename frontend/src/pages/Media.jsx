import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import GallerySection from '../components/GallerySection'
import Lightbox from '../components/Lightbox'
import { ArrowRight, ExternalLink, Images } from 'lucide-react'
import { DataState } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Media.css'

const CATEGORY_TABS = [
  { value: 'events', label: 'Events' },
  { value: 'health-camps', label: 'Health Camps' },
  { value: 'community-outreach', label: 'Community Outreach' },
  { value: 'facilities', label: 'Facilities' },
  { value: 'press', label: 'Press Coverage' },
]

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
  const { data: slides } = useApi(() => fetchList('/hero-slides/'), [], [])
  const bannerSlide = (slides || []).find((s) => s.is_published !== false)
  const location = useLocation()
  const [filter, setFilter] = useState('all')

  // Filter tabs only for categories that events actually use (set per event in the admin).
  const usedCategories = CATEGORY_TABS.filter((tab) => (events || []).some((e) => e.category === tab.value))
  const visibleEvents = filter === 'all' ? events : (events || []).filter((e) => e.category === filter)

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

  return (
    <div>
      <PageHero
        eyebrow="Media"
        title="Events, camps &amp; coverage"
        description="Photo galleries from CRTDH events, health camps and outreach programmes, plus press coverage."
        image={bannerSlide?.image}
        imagePosition={bannerSlide?.image_position}
      />

      <section className="section">
        <div className="container">
          {usedCategories.length > 0 && (
            <div className="media-filters" role="group" aria-label="Filter galleries">
              {[{ value: 'all', label: 'All' }, ...usedCategories].map((tab) => (
                <button
                  type="button"
                  key={tab.value}
                  className={`media-filter${filter === tab.value ? ' is-active' : ''}`}
                  aria-pressed={filter === tab.value}
                  onClick={() => setFilter(tab.value)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
          <DataState
            loading={loading}
            error={error}
            data={visibleEvents}
            emptyProps={{ title: 'Media galleries coming soon' }}
          >
            {(items) => (
              <div className="media-events">
                {items.map((event, i) => (
                  <Reveal as="div" className="media-event" id={event.slug} key={event.id} delay={Math.min(i, 4) * 0.05}>
                    <GallerySection 
                      title={event.title} 
                      description={event.description}
                      date={event.event_date}
                      category={event.category}
                      images={event.images} 
                      onImageClick={(index) => openLightbox(event.images, index)} 
                    />
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
            <Reveal>
              <GallerySection 
                title="More from CRTDH" 
                description="Additional photos from our campus, team, and facility."
                images={galleryImages} 
                onImageClick={(index) => openLightbox(galleryImages, index)} 
              />
            </Reveal>
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

      <section className="section media-cta-section">
        <div className="container">
          <div className="media-cta">
            <span className="media-cta__icon" aria-hidden="true">
              <Images size={26} />
            </span>
            <div className="media-cta__text">
              <h2>Looking for something specific?</h2>
              <p>Get in touch with us for media enquiries or photos from a particular event.</p>
            </div>
            <Link to="/contact" className="btn btn--primary">
              Contact us <ArrowRight size={17} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

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
