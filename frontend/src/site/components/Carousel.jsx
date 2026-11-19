import { useCallback, useEffect, useRef, useState } from 'react'
import useEmblaCarousel from 'embla-carousel-react'
import './Carousel.css'

/**
 * Generic autoplaying carousel with manual prev/next arrows and dot
 * indicators. `items` is rendered via the `renderItem` render-prop so this
 * one component serves both the hero-slides and project-slides carousels.
 */
export default function Carousel({ items, renderItem, autoplayDelay = 5000, className = '', ariaLabel }) {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true })
  const [selectedIndex, setSelectedIndex] = useState(0)
  const autoplayRef = useRef(null)

  const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi])
  const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi])
  const scrollTo = useCallback((i) => emblaApi && emblaApi.scrollTo(i), [emblaApi])

  useEffect(() => {
    if (!emblaApi) return
    const onSelect = () => setSelectedIndex(emblaApi.selectedScrollSnap())
    emblaApi.on('select', onSelect)
    onSelect()
    return () => emblaApi.off('select', onSelect)
  }, [emblaApi])

  // Autoplay, paused on hover/focus, restarted after manual navigation.
  useEffect(() => {
    if (!emblaApi || items.length <= 1) return undefined

    const stop = () => {
      if (autoplayRef.current) {
        clearInterval(autoplayRef.current)
        autoplayRef.current = null
      }
    }
    const start = () => {
      stop()
      autoplayRef.current = setInterval(() => {
        emblaApi.scrollNext()
      }, autoplayDelay)
    }

    start()
    const rootNode = emblaApi.rootNode()
    rootNode.addEventListener('mouseenter', stop)
    rootNode.addEventListener('mouseleave', start)
    rootNode.addEventListener('focusin', stop)
    rootNode.addEventListener('focusout', start)

    return () => {
      stop()
      rootNode.removeEventListener('mouseenter', stop)
      rootNode.removeEventListener('mouseleave', start)
      rootNode.removeEventListener('focusin', stop)
      rootNode.removeEventListener('focusout', start)
    }
  }, [emblaApi, autoplayDelay, items.length])

  if (!items || items.length === 0) return null

  return (
    <div className={`carousel ${className}`} aria-roledescription="carousel" aria-label={ariaLabel}>
      <div className="carousel__viewport" ref={emblaRef}>
        <div className="carousel__container">
          {items.map((item, i) => (
            <div className="carousel__slide" key={item.id ?? i}>
              {renderItem(item, i)}
            </div>
          ))}
        </div>
      </div>

      {items.length > 1 && (
        <>
          <button
            type="button"
            className="carousel__arrow carousel__arrow--prev"
            onClick={scrollPrev}
            aria-label="Previous slide"
          >
            ‹
          </button>
          <button
            type="button"
            className="carousel__arrow carousel__arrow--next"
            onClick={scrollNext}
            aria-label="Next slide"
          >
            ›
          </button>

          <div className="carousel__dots">
            {items.map((item, i) => (
              <button
                key={item.id ?? i}
                type="button"
                className={`carousel__dot ${i === selectedIndex ? 'is-active' : ''}`}
                aria-label={`Go to slide ${i + 1}`}
                onClick={() => scrollTo(i)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
