import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import GallerySection from '../components/GallerySection'
import Lightbox from '../components/Lightbox'
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
                  <Reveal as="div" className="media-event" id={event.slug} key={event.id} delay={Math.min(i, 4) * 0.05}>
                    <GallerySection 
                      title={event.title} 
                      description={event.description}
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
