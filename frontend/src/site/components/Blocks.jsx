import { useEffect, useRef, useState } from 'react'
import { Img } from '../media.jsx'
import { paragraphs, youtubeId } from '../util.js'

/**
 * Inner-page banner (reading mode): H1 in Fraunces, one sentence, optional print.
 * Same on every inner page; no hero theatre.
 */
export function PageBanner({ title, intro, image, imageAlt = '', children }) {
  return (
    <header className={`banner${image ? ' banner--print' : ''}`}>
      <div className="wrap banner__inner">
        <div className="banner__text">
          <h1>{title}</h1>
          {intro && <p className="banner__intro">{intro}</p>}
          {children}
        </div>
        {image && (
          <div className="banner__print">
            <Img src={image} alt={imageAlt} ratio="3x2" sizes="(min-width: 768px) 40vw, 100vw" priority />
          </div>
        )}
      </div>
    </header>
  )
}

export function Prose({ text, className = '' }) {
  const ps = paragraphs(text)
  if (!ps.length) return null
  return (
    <div className={`prose ${className}`}>
      {ps.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  )
}

/** Rich text from the CMS (sanitised on the server: b, i, a, ul, ol, h3). */
export function RichText({ html, className = '' }) {
  if (!html) return null
  return <div className={`prose ${className}`} dangerouslySetInnerHTML={{ __html: html }} />
}

/** YouTube poster that loads the player only when pressed (no third-party requests before). */
export function VideoPoster({ url, title }) {
  const [playing, setPlaying] = useState(false)
  const id = youtubeId(url)
  if (!id) return null
  return (
    <figure className="video">
      <div className="video__frame r-16x9">
        {playing ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`}
            title={title || 'Video'}
            allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <button type="button" className="video__poster" onClick={() => setPlaying(true)}>
            <img src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`} alt="" loading="lazy" width="480" height="360" />
            <span className="video__play">
              <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3l12 7-12 7z" fill="currentColor" /></svg>
              <span>Play video<span className="visually-hidden">: {title}</span></span>
            </span>
          </button>
        )}
      </div>
      {title && <figcaption>{title}</figcaption>}
    </figure>
  )
}

/**
 * Photo gallery: a 3:2 grid; any photo opens a full-size viewer (native <dialog>).
 * `limit` shows the first N and a "Show all" control; all photos stay in the HTML.
 */
export function Gallery({ items, title, limit = 0, columns = 3 }) {
  const [index, setIndex] = useState(-1)
  const [expanded, setExpanded] = useState(false)
  const dialog = useRef(null)
  const list = (items || []).filter((i) => i && i.image)
  const open = index >= 0

  useEffect(() => {
    const d = dialog.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])

  if (!list.length) return null
  const shown = limit && !expanded ? list.slice(0, limit) : list
  const step = (delta) => setIndex((i) => (i + delta + list.length) % list.length)
  const current = list[index] || list[0]
  const label = (item, i) => item.caption || `${title || 'Photo'} — photo ${i + 1} of ${list.length}`

  return (
    <div className="gallery">
      <ul className={`gallery__grid gallery__grid--${columns}`}>
        {shown.map((item, i) => (
          <li key={item.id ?? i}>
            <button type="button" className="gallery__item" onClick={() => setIndex(i)} aria-label={`Open ${label(item, i)}`}>
              <Img src={item.image} alt={item.caption || ''} ratio="3x2" sizes="(min-width: 1024px) 30vw, (min-width: 768px) 45vw, 100vw" />
            </button>
            {item.caption && <p className="gallery__caption">{item.caption}</p>}
          </li>
        ))}
      </ul>
      {limit > 0 && list.length > limit && (
        <button type="button" className="text-link gallery__more" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Show fewer photos' : `Show all ${list.length} photos`}
        </button>
      )}
      <dialog
        ref={dialog}
        className="viewer"
        aria-label={title ? `${title} photos` : 'Photos'}
        onClose={() => setIndex(-1)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') step(1)
          if (e.key === 'ArrowLeft') step(-1)
        }}
        onClick={(e) => {
          if (e.target === dialog.current) setIndex(-1)
        }}
      >
        {open && (
          <div className="viewer__body">
            <img src={current.image} alt={current.caption || ''} className="viewer__img" />
            <div className="viewer__bar">
              <p aria-live="polite">
                {current.caption ? `${current.caption} · ` : ''}
                {index + 1} of {list.length}
              </p>
              <div className="viewer__controls">
                <button type="button" className="btn btn--secondary" onClick={() => step(-1)}>Previous</button>
                <button type="button" className="btn btn--secondary" onClick={() => step(1)}>Next</button>
                <button type="button" className="btn btn--primary" onClick={() => setIndex(-1)} autoFocus>Close</button>
              </div>
            </div>
          </div>
        )}
      </dialog>
    </div>
  )
}

/** A titled image-grid block from the CMS (keeps its anchor for deep links). */
export function GridBlock({ block, headingLevel = 2, limit = 0, extraAnchor }) {
  if (!block || !(block.items || []).length) return null
  const H = `h${headingLevel}`
  return (
    <section className="block" id={block.anchor_slug || undefined} aria-labelledby={`block-${block.id}`}>
      {extraAnchor && <span id={extraAnchor} className="anchor" />}
      <div className="section-head">
        <H id={`block-${block.id}`}>{block.section_title}</H>
        {block.intro && <p>{block.intro}</p>}
      </div>
      <Gallery items={block.items} title={block.section_title} limit={limit} />
    </section>
  )
}
