import { useEffect, useRef, useState } from 'react'
import SiteLink from '../link.jsx'
import { Img } from '../media.jsx'
import { paragraphs, youtubeId } from '../util.js'
import { hasMarkup, sanitizeRichText } from '../richtext.js'

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

/**
 * Rich text from the CMS (every registry field of type richtext: about-page intro, mission_vision, dsir_about,
 * iitkgp_about; innovations body). The backend cleans these on write with the allow-list p, br, strong/b, em/i,
 * a, ul, ol, li, h3; sanitizeRichText applies the same allow-list again here. Plain text (no markup) is shown as
 * paragraphs, like Prose.
 */
export function RichText({ html, className = '' }) {
  if (!html) return null
  if (!hasMarkup(html)) return <Prose text={html} className={className} />
  const clean = sanitizeRichText(html)
  if (!clean.trim()) return null
  // nosemgrep: crtdh-no-dangerously-set-inner-html, typescript.react.security.audit.react-dangerouslysetinnerhtml.react-dangerouslysetinnerhtml -- rebuilt from an allow-list by sanitizeRichText (src/site/richtext.js); backend clean_richtext on write
  return <div className={`prose ${className}`} dangerouslySetInnerHTML={{ __html: clean }} />
}

/** Google map that loads only when pressed (no third-party requests on page load), with a directions link. */
export function MapEmbed({ src, address }) {
  const [shown, setShown] = useState(false)
  // Only Google's embed endpoint may be framed (the CSP frame-src allows nothing else).
  if (!src || !src.startsWith('https://www.google.com/maps/embed')) return null
  const directions = address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}` : null
  return (
    <div className="map" data-map-embed>
      {shown ? (
        <iframe src={src} title="Map: CRTDH at IIT Kharagpur" referrerPolicy="no-referrer-when-downgrade" />
      ) : (
        <div className="map__facade">
          <p className="map__label">Map of the centre</p>
          <button type="button" className="btn btn--secondary" onClick={() => setShown(true)}>Show the map</button>
          <p className="small soft">Loads Google Maps.</p>
          {directions && <a href={directions} className="text-link" target="_blank" rel="noopener noreferrer">Directions in Google Maps</a>}
        </div>
      )}
    </div>
  )
}

/**
 * YouTube poster that loads the player (youtube-nocookie) only when pressed; no third-party requests before.
 * With `image` (a related event photograph from the snapshot) the poster is that photograph with the title on
 * it; without one it is a typographic poster on the navy field. Never an empty box, never a YouTube thumbnail.
 */
export function VideoPoster({ url, title, image }) {
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
          <button
            type="button"
            className={`video__poster ${image ? 'video__poster--photo' : 'video__poster--type'}`}
            onClick={() => setPlaying(true)}
            data-youtube={id}
          >
            {/* Decorative inside the button: its name is "Play video: <title>". */}
            {image && <Img src={image} alt="" ratio={null} className="video__photo" sizes="(min-width: 768px) 48vw, 100vw" />}
            {title && <span className="video__title" aria-hidden="true">{title}</span>}
            <span className="video__play">
              <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3l12 7-12 7z" fill="currentColor" /></svg>
              <span>Play video<span className="visually-hidden">: {title}</span></span>
            </span>
          </button>
        )}
      </div>
      {title && playing && <figcaption>{title}</figcaption>}
    </figure>
  )
}

/** The first photograph of a media event whose title or slug matches `title` (e.g. a video of the same event). */
export function eventPhotoFor(title, events) {
  const norm = (v) => String(v || '').toLowerCase().replace(/[^a-z0-9]/g, '')
  const key = norm(title)
  if (!key) return null
  const ev = (events || []).find((e) => norm(e.slug) === key || norm(e.title) === key)
  return (ev?.images || []).find((im) => im && im.image) || null
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
              <Img src={item.image} alt={item.image_alt || item.caption || ''} ratio="3x2" sizes="(min-width: 1024px) 30vw, (min-width: 768px) 45vw, 100vw" />
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
            <img src={current.image} alt={current.image_alt || current.caption || ''} className="viewer__img" />
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

/** Closing band at the foot of a page: one sentence and one action. `surface` alternates the ground. */
export function ClosingBand({ id, title, text, action, to = '/contact/', surface = false }) {
  return (
    <section className={`section${surface ? ' section--surface' : ''}`} aria-labelledby={id}>
      <div className="wrap closing">
        <h2 id={id}>{title}</h2>
        {text && <p className="lead">{text}</p>}
        <div className="actions">
          <SiteLink to={to} className="btn btn--primary">{action}</SiteLink>
        </div>
      </div>
    </section>
  )
}
