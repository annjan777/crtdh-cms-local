import { useRef } from 'react'
import { useParallax } from './motion4.js'
import { usePageData } from '../api/data.jsx'
import './PageHero.css'

// Inner-page hero in the home page's language: a forest-green panel with the title on the left, an optional
// photo that starts where the copy ends and fades out of the green, and the sage + ivory wave below.
// With `page`, the CMS page header for that page (collection "page-heroes") wins field by field; the props are
// the built-in wording and the page's own photo choice, used where the CMS field is empty.
export default function PageHero({ page, eyebrow, title, description, image, imagePosition }) {
  const ref = useRef(null)
  const data = usePageData()
  const cms = page ? (data?.collections?.['page-heroes'] || []).find((h) => h && h.page === page && h.is_published !== false) : null
  const e = cms?.eyebrow || eyebrow
  const t = cms?.title || title
  const d = cms?.description || description
  const img = cms?.image || image
  const pos = (cms?.image && cms?.image_position) || imagePosition
  useParallax(ref, [img])
  return (
    <div className={`page-hero${img ? ' page-hero--photo' : ''}`} ref={ref} data-block={page ? `${page}.hero` : undefined}>
      {img && (
        <div className="page-hero__media" data-px="0.12" aria-hidden="true">
          <img src={img} alt="" style={pos ? { objectPosition: pos } : undefined} fetchPriority="high" />
        </div>
      )}
      <div className="container page-hero__inner">
        {e && e.trim().toLowerCase() !== String(t || '').trim().toLowerCase() && <span className="eyebrow eyebrow--on-dark">{e}</span>}
        <h1 className="page-hero__title">{t}</h1>
        {d && <p className="page-hero__desc">{d}</p>}
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
