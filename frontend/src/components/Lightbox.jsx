import { useEffect, useCallback } from 'react'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'
import './Lightbox.css'

export default function Lightbox({ images, currentIndex, onClose, onNext, onPrev }) {
  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') onNext()
      if (e.key === 'ArrowLeft') onPrev()
    },
    [onClose, onNext, onPrev]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    // Prevent body scrolling
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  if (!images || images.length === 0) return null

  const currentImage = images[currentIndex]
  const src = currentImage.image || currentImage.logo || currentImage.src
  const caption = currentImage.caption || currentImage.title || ''

  return (
    <div className="lightbox-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose} aria-label="Close lightbox">
          <X size={28} />
        </button>

        <div className="lightbox-image-container">
          <button 
            className="lightbox-nav lightbox-nav--prev" 
            onClick={onPrev}
            disabled={images.length <= 1}
            aria-label="Previous image"
          >
            <ChevronLeft size={36} />
          </button>

          <figure className="lightbox-figure">
            <img src={src} alt={caption || `Image ${currentIndex + 1}`} />
            <figcaption>
              <span className="lightbox-counter">{currentIndex + 1} / {images.length}</span>
              {caption && <span className="lightbox-caption">{caption}</span>}
            </figcaption>
          </figure>

          <button 
            className="lightbox-nav lightbox-nav--next" 
            onClick={onNext}
            disabled={images.length <= 1}
            aria-label="Next image"
          >
            <ChevronRight size={36} />
          </button>
        </div>
      </div>
    </div>
  )
}
