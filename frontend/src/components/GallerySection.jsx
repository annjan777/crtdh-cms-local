import { useState } from 'react'
import { Camera, ChevronLeft, ChevronRight, CalendarDays, Stethoscope, Users, Building2, Newspaper, PartyPopper } from 'lucide-react'
import './GallerySection.css'

const CATEGORY_ICONS = {
  events: PartyPopper,
  'health-camps': Stethoscope,
  'community-outreach': Users,
  facilities: Building2,
  press: Newspaper,
}

const MAX_THUMBNAILS = 6

function formatDate(isoDate) {
  if (!isoDate) return ''
  const d = new Date(`${isoDate}T00:00:00`)
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * One gallery event: header (icon, title, optional description and date), a featured photo the
 * visitor can step through, and a grid of thumbnails ending in "+N more". Any photo opens the lightbox.
 */
export default function GallerySection({ title, description, date, category, images, onImageClick }) {
  const [featured, setFeatured] = useState(0)
  if (!images || images.length === 0) return null

  const Icon = CATEGORY_ICONS[category] || Camera
  const current = images[featured] || images[0]
  const thumbnails = images.slice(0, MAX_THUMBNAILS)
  const remaining = images.length - MAX_THUMBNAILS
  const src = (img) => img.image || img.logo || img.src
  const step = (delta) => setFeatured((i) => (i + delta + images.length) % images.length)
  const dateLabel = formatDate(date)

  return (
    <div className="gallery-section">
      <div className="gallery-section__header">
        <div className="gallery-section__title-wrap">
          <div className={`gallery-section__icon gallery-section__icon--${category || 'default'}`} aria-hidden="true">
            <Icon size={22} />
          </div>
          <div className="gallery-section__title-text">
            <h3>{title}</h3>
            {description && <p>{description}</p>}
          </div>
        </div>
        <button type="button" className="gallery-section__view-all" onClick={() => onImageClick(0)}>
          View all {images.length} photos <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="gallery-section__layout">
        <div className="gallery-section__featured">
          <button
            type="button"
            className="gallery-section__featured-open"
            onClick={() => onImageClick(featured)}
            aria-label={`Open photo ${featured + 1} of ${images.length}: ${current.caption || title}`}
          >
            <img src={src(current)} alt={current.caption || title} loading="lazy" />
            <span className="gallery-section__featured-overlay">
              <span className="gallery-section__featured-title">{current.caption || title}</span>
              {dateLabel && (
                <span className="gallery-section__featured-date">
                  <CalendarDays size={14} aria-hidden="true" /> {dateLabel}
                </span>
              )}
            </span>
          </button>
          {images.length > 1 && (
            <>
              <button type="button" className="gallery-section__nav gallery-section__nav--prev" onClick={() => step(-1)} aria-label="Previous photo">
                <ChevronLeft size={18} aria-hidden="true" />
              </button>
              <button type="button" className="gallery-section__nav gallery-section__nav--next" onClick={() => step(1)} aria-label="Next photo">
                <ChevronRight size={18} aria-hidden="true" />
              </button>
              <span className="gallery-section__counter" aria-live="polite">
                {featured + 1} / {images.length}
              </span>
            </>
          )}
        </div>

        {thumbnails.length > 1 && (
          <div className="gallery-section__thumbnails">
            {thumbnails.map((thumb, index) => {
              const showMore = index === thumbnails.length - 1 && remaining > 0
              return (
                <button
                  type="button"
                  key={thumb.id || index}
                  className={`gallery-section__thumb${index === featured ? ' is-current' : ''}`}
                  onClick={() => (showMore ? onImageClick(index) : setFeatured(index))}
                  aria-label={showMore ? `Open all photos (${remaining} more)` : `Show photo ${index + 1}${thumb.caption ? `: ${thumb.caption}` : ''}`}
                >
                  <img src={src(thumb)} alt="" loading="lazy" />
                  {showMore && (
                    <span className="gallery-section__more-overlay">+{remaining} more</span>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
