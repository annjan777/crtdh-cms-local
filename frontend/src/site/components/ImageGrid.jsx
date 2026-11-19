import { ImageOff } from 'lucide-react'
import './ImageGrid.css'

/**
 * Responsive gallery grid. `items` are objects with at least an `image`
 * (or `logo`) URL; `caption`/`title`/`name` supplies the label shown under
 * the image. Used for equipment, services, enterprises, generic
 * image-grid-items and gallery-images.
 */
function getInitials(name) {
  if (!name) return '?'
  const words = name.split(' ').filter(w => w.trim().length > 0)
  if (words.length === 1) return words[0].substring(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

// headingLevel: the label is also a heading (h3, h4…) so screen-reader users can jump item to item; it looks the
// same as a plain caption. The photo's alt is then empty, since the heading already names it.
export default function ImageGrid({ items, columns = 4, imageKey = 'image', labelKey, aspect = 'square', headingLevel }) {
  const H = headingLevel ? `h${headingLevel}` : null
  if (!items || items.length === 0) return null

  return (
    <div className={`image-grid image-grid--cols-${columns}`}>
      {items.map((item, i) => {
        const src = item[imageKey] || item.image || item.logo
        const label = labelKey ? item[labelKey] : item.caption || item.title || item.name
        return (
          <figure className={`image-grid__item card image-grid__item--${aspect}`} key={item.id ?? i}>
            <div className="image-grid__frame">
              {src ? (
                <img src={src} alt={H ? '' : label || ''} loading="lazy" />
              ) : (
                <div className="image-grid__text-logo">
                  <span>{getInitials(label)}</span>
                </div>
              )}
            </div>
            {label && <figcaption>{H ? <H className="image-grid__heading">{label}</H> : label}</figcaption>}
          </figure>
        )
      })}
    </div>
  )
}
