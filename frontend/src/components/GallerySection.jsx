import { Camera, Image as ImageIcon } from 'lucide-react'
import './GallerySection.css'

export default function GallerySection({ title, description, images, onImageClick }) {
  if (!images || images.length === 0) return null

  const featuredImage = images[0]
  // We'll show up to 6 thumbnails (2 rows of 3)
  const MAX_THUMBNAILS = 6
  const thumbnails = images.slice(1, MAX_THUMBNAILS + 1)
  const remainingCount = images.length - (MAX_THUMBNAILS + 1)

  return (
    <div className="gallery-section">
      <div className="gallery-section__header">
        <div className="gallery-section__title-wrap">
          <div className="gallery-section__icon" aria-hidden="true">
            <Camera size={20} />
          </div>
          <div className="gallery-section__title-text">
            <h3>{title}</h3>
            {description && <p>{description}</p>}
          </div>
        </div>
        <button 
          className="gallery-section__view-all" 
          onClick={() => onImageClick(0)}
        >
          View all photos
        </button>
      </div>

      <div className="gallery-section__layout">
        {/* Left: Featured Image */}
        <div 
          className="gallery-section__featured"
          onClick={() => onImageClick(0)}
          role="button"
          tabIndex={0}
          aria-label={`View ${featuredImage.caption || title}`}
        >
          <img 
            src={featuredImage.image || featuredImage.logo || featuredImage.src} 
            alt={featuredImage.caption || title} 
            loading="lazy"
          />
          <div className="gallery-section__featured-overlay">
            <span className="gallery-section__featured-title">{title}</span>
            {featuredImage.caption && (
              <span className="gallery-section__featured-caption">{featuredImage.caption}</span>
            )}
          </div>
        </div>

        {/* Right: Thumbnails */}
        {thumbnails.length > 0 && (
          <div className="gallery-section__thumbnails">
            {thumbnails.map((thumb, index) => {
              const isLast = index === thumbnails.length - 1
              const hasMore = remainingCount > 0
              const actualIndex = index + 1 // offset by 1 because of featured image

              return (
                <div 
                  key={thumb.id || index} 
                  className="gallery-section__thumb"
                  onClick={() => onImageClick(actualIndex)}
                  role="button"
                  tabIndex={0}
                  aria-label={`View image ${actualIndex + 1}`}
                >
                  <img 
                    src={thumb.image || thumb.logo || thumb.src} 
                    alt={thumb.caption || `${title} photo ${actualIndex + 1}`}
                    loading="lazy"
                  />
                  {isLast && hasMore && (
                    <div className="gallery-section__more-overlay">
                      <span>+{remainingCount} more</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
