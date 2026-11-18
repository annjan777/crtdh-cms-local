import { createContext, useContext } from 'react'

// The snapshot's `media` map: { "/media/<hash>.<ext>": { width, height, variants: { avif, webp }, lqip? } }
const MediaContext = createContext({})

export function MediaProvider({ media, children }) {
  return <MediaContext.Provider value={media || {}}>{children}</MediaContext.Provider>
}

export function useMedia(src) {
  const map = useContext(MediaContext)
  return (src && map && map[src]) || null
}

// Variants may be listed as URL strings ("/media/abc-800.avif") or as { url|src, width }.
function toSrcset(list) {
  if (!Array.isArray(list) || list.length === 0) return null
  const parts = list
    .map((v) => {
      if (typeof v === 'string') {
        const m = v.match(/-(\d+)w?\.\w+$/)
        return m ? `${v} ${m[1]}w` : v
      }
      const url = v.url || v.src
      return url && v.width ? `${url} ${v.width}w` : url
    })
    .filter(Boolean)
  return parts.length ? parts.join(', ') : null
}

/**
 * A photograph in a fixed-ratio frame. Uses AVIF/WebP variants from the snapshot
 * when present, otherwise the original URL. The frame shows the LQIP colour (or
 * the neutral placeholder tone) until the image paints, so nothing shifts.
 */
export function Img({ src, alt = '', ratio = '3x2', sizes = '100vw', priority = false, contain = false, figure = false, className = '', style }) {
  const info = useMedia(src)
  if (!src) return null
  const avif = toSrcset(info?.variants?.avif)
  const webp = toSrcset(info?.variants?.webp)
  const bg = info?.lqip || info?.color || info?.dominant_color
  const cls = ['img', ratio ? `r-${ratio}` : '', contain ? 'img--contain' : '', figure ? 'img--figure' : '', className].filter(Boolean).join(' ')
  const img = (
    <img
      src={src}
      alt={alt}
      width={info?.width || undefined}
      height={info?.height || undefined}
      loading={priority ? 'eager' : 'lazy'}
      decoding={priority ? 'sync' : 'async'}
      fetchPriority={priority ? 'high' : undefined}
      sizes={avif || webp ? sizes : undefined}
    />
  )
  return (
    <div className={cls} style={bg ? { ...style, backgroundColor: bg } : style}>
      {avif || webp ? (
        <picture>
          {avif && <source type="image/avif" srcSet={avif} sizes={sizes} />}
          {webp && <source type="image/webp" srcSet={webp} sizes={sizes} />}
          {img}
        </picture>
      ) : (
        img
      )}
    </div>
  )
}
