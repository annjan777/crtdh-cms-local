import { useEffect, useRef, useState } from 'react'
import { Img } from '../media.jsx'

const HOLD_MS = 8000

/**
 * Home hero photographs: at most four slides crossfading in one print (approved d3).
 * The first slide is the LCP image. Autoplay holds 8 s with a visible Pause; it stops
 * on hover, keyboard focus or a hidden tab, and never runs under reduced motion.
 * The small print previews the next photograph and advances to it.
 */
export default function HeroPrints({ slides }) {
  const list = slides.slice(0, 4)
  const [active, setActive] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [held, setHeld] = useState(false)
  const root = useRef(null)
  const count = list.length

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!reduce && count > 1) setPlaying(true)
  }, [count])

  useEffect(() => {
    if (!playing || held || count < 2) return undefined
    const t = setTimeout(() => {
      if (document.visibilityState === 'visible') setActive((i) => (i + 1) % count)
    }, HOLD_MS)
    return () => clearTimeout(t)
  }, [playing, held, active, count])

  if (!count) return null
  const next = (active + 1) % count
  const go = (i) => setActive((i + count) % count)

  return (
    <div
      className="hero__prints"
      ref={root}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={(e) => {
        if (!root.current?.contains(e.relatedTarget)) setHeld(false)
      }}
    >
      <div className="hero__print hero__print--large" role="group" aria-roledescription="carousel" aria-label="Photographs from the centre">
        {list.map((s, i) => (
          <div
            key={s.id ?? i}
            className={`hero__slide${i === active ? ' is-active' : ''}`}
            aria-hidden={i === active ? undefined : 'true'}
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} of ${count}`}
          >
            <Img
              src={s.image}
              alt={s.alt_text || ''}
              ratio={null}
              priority={i === 0}
              sizes="(min-width: 768px) 58vw, 100vw"
              style={s.image_position ? { '--pos': s.image_position } : undefined}
            />
          </div>
        ))}
      </div>
      {count > 1 && (
        <>
          <button type="button" className="hero__print hero__print--small" onClick={() => go(next)} aria-label={`Show photograph ${next + 1} of ${count}`}>
            <Img src={list[next].image} alt="" ratio="1x1" sizes="160px" />
          </button>
          <div className="hero__controls">
            <p className="hero__count" aria-live={playing && !held ? 'off' : 'polite'}>
              Photograph {active + 1} of {count}
            </p>
            <button type="button" className="icon-btn" onClick={() => go(active - 1)} aria-label="Previous photograph">
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3L5 9l6 6" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            </button>
            <button type="button" className="icon-btn" onClick={() => go(active + 1)} aria-label="Next photograph">
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M7 3l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            </button>
            <button type="button" className="icon-btn icon-btn--text" onClick={() => setPlaying((p) => !p)} aria-pressed={!playing}>
              {playing ? 'Pause' : 'Play'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
