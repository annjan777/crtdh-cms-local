import { useState } from 'react'
import { Expand } from 'lucide-react'
import Lightbox from './Lightbox'
import './PhotoMosaic.css'

/** A block of CMS photos as an asymmetric mosaic (first photo large) that opens in a lightbox. */
export default function PhotoMosaic({ items, label }) {
  const list = (items || []).filter((it, i, self) => it.image && self.findIndex((t) => t.image === it.image) === i)
  const [at, setAt] = useState(-1)
  if (!list.length) return null
  return (
    <>
      <div className="mosaic">
        {list.map((it, k) => (
          <button type="button" className="mosaic__cell zoom" key={it.id ?? k} onClick={() => setAt(k)} data-rv={k === 0 ? 'mask' : 'fade'} style={{ '--d': `${Math.min(k, 6) * 70}ms` }}>
            <img src={it.image} alt={it.caption || ''} loading="lazy" />
            {it.caption && <span className="mosaic__cap">{it.caption}</span>}
            <span className="mosaic__open" aria-hidden="true"><Expand size={16} /></span>
            <span className="visually-hidden">{label ? `${label}: ` : ''}open photo {k + 1} of {list.length}</span>
          </button>
        ))}
      </div>
      {at >= 0 && (
        <Lightbox
          images={list}
          currentIndex={at}
          onClose={() => setAt(-1)}
          onNext={() => setAt((i) => (i + 1) % list.length)}
          onPrev={() => setAt((i) => (i - 1 + list.length) % list.length)}
        />
      )}
    </>
  )
}
