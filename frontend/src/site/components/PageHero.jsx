import { useRef } from 'react'
import { useParallax } from './motion4.js'
import './PageHero.css'

// Inner-page hero in the home page's language: a forest-green panel with the title on the left, an optional
// CMS photo that starts where the copy ends and fades out of the green, and the sage + ivory wave below.
// `image` is always a photo the page already has from the CMS; without one the panel stands alone.
export default function PageHero({ eyebrow, title, description, image, imagePosition }) {
  const ref = useRef(null)
  useParallax(ref, [image])
  return (
    <div className={`page-hero${image ? ' page-hero--photo' : ''}`} ref={ref}>
      {image && (
        <div className="page-hero__media" data-px="0.12" aria-hidden="true">
          <img src={image} alt="" style={imagePosition ? { objectPosition: imagePosition } : undefined} fetchPriority="high" />
        </div>
      )}
      <div className="container page-hero__inner">
        {eyebrow && <span className="eyebrow eyebrow--on-dark">{eyebrow}</span>}
        <h1 className="page-hero__title">{title}</h1>
        {description && <p className="page-hero__desc">{description}</p>}
      </div>
      <svg className="page-hero__wave" viewBox="0 0 1600 120" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path className="page-hero__wave-sage" d="M0 40 C 160 96 330 112 560 92 L 560 120 L 0 120 Z" />
        <path className="page-hero__wave-ivory" d="M0 96 C 260 82 520 40 760 46 C 980 52 1060 116 1240 118 C 1400 120 1500 100 1600 88 L 1600 120 L 0 120 Z" />
      </svg>
    </div>
  )
}

// A photo from a list of CMS image-grid blocks (block.items[].image), for a page hero: the `nth` (0 = first).
export function firstBlockImage(blocks, nth = 0) {
  const all = []
  for (const b of blocks || []) for (const it of b?.items || []) if (it?.image) all.push(it.image)
  return all[nth] || all[0] || null
}
