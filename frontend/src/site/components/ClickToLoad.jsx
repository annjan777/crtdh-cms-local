import { useState } from 'react'
import { MapPin, Play } from 'lucide-react'
import { mapEmbedUrl, youtubeId } from '../util.js'
import './ClickToLoad.css'

// Third-party embeds load only when the visitor asks for them (R-8 / F-06).
// Before the click the page makes no request to Google or YouTube; the box keeps
// its size, so the layout does not move when the embed swaps in.

export function youtubeEmbedUrl(url, { autoplay = false } = {}) {
  const id = youtubeId(url)
  if (!id || !/^[\w-]{6,20}$/.test(id)) return null
  return `https://www.youtube-nocookie.com/embed/${id}?rel=0${autoplay ? '&autoplay=1' : ''}`
}

/** YouTube player behind a "Play video" poster. Renders nothing for a URL that is not a YouTube video. */
export function YouTubeFacade({ url, title }) {
  const [playing, setPlaying] = useState(false)
  const src = youtubeEmbedUrl(url, { autoplay: true })
  if (!src) return null
  if (playing) {
    return (
      <iframe
        className="ctl-frame"
        src={src}
        title={title || 'Video'}
        allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
      />
    )
  }
  return (
    <button type="button" className="ctl-poster" onClick={() => setPlaying(true)} data-youtube={youtubeId(url)}>
      {title && (
        <span className="ctl-poster__title" aria-hidden="true">
          {title}
        </span>
      )}
      <span className="ctl-poster__action">
        <span className="ctl-poster__icon" aria-hidden="true">
          <Play size={18} fill="currentColor" />
        </span>
        <span>
          Play video<span className="visually-hidden">{title ? `: ${title}` : ''}</span>
        </span>
      </span>
      <span className="ctl-poster__note">Plays from YouTube</span>
    </button>
  )
}

/** A Google Maps search for the address: opens directions without embedding anything. */
export function directionsUrl(address) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address || 'CRTDH, IIT Kharagpur')}`
}

/** Google map behind a "Show the map" button, with a directions link that needs no embed. */
export function MapFacade({ src, title = 'CRTDH location map', address }) {
  const [shown, setShown] = useState(false)
  const embed = mapEmbedUrl(src)
  if (!embed) return null
  if (shown) {
    return <iframe className="ctl-frame" src={embed} title={title} referrerPolicy="no-referrer-when-downgrade" />
  }
  const directions = address ? directionsUrl(address) : null
  return (
    <div className="ctl-map" data-map-embed>
      <span className="ctl-map__pin" aria-hidden="true">
        <MapPin size={22} />
      </span>
      <p className="ctl-map__label">Map of the centre</p>
      {address && <p className="ctl-map__address">{address}</p>}
      <button type="button" className="btn btn--primary ctl-map__btn" onClick={() => setShown(true)}>
        Show the map
      </button>
      <p className="ctl-map__note">Loads Google Maps.</p>
      {directions && (
        <a href={directions} className="ctl-map__link" target="_blank" rel="noopener noreferrer">
          Directions in Google Maps
        </a>
      )}
    </div>
  )
}
