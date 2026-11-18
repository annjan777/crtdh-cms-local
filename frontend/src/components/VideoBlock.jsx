import { useState } from 'react'
import { Play } from 'lucide-react'
import './VideoBlock.css'

function youtubeId(youtubeUrl) {
  try {
    const url = new URL(youtubeUrl)
    if (url.hostname.includes('youtu.be')) return url.pathname.slice(1)
    if (url.pathname.startsWith('/embed/')) return url.pathname.split('/')[2]
    return url.searchParams.get('v')
  } catch {
    return null
  }
}

/**
 * Shows the YouTube thumbnail with a play button and only loads the player when
 * someone presses play, so the page doesn't show blank black boxes or load
 * every embedded player up front.
 */
export default function VideoBlock({ block }) {
  const [playing, setPlaying] = useState(false)
  if (!block) return null

  const id = block.youtube_url ? youtubeId(block.youtube_url) : null
  const title = block.title || 'Video'

  let frame
  if (id && playing) {
    frame = (
      <iframe
        src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`}
        title={title}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    )
  } else if (id) {
    frame = (
      <button type="button" className="video-block__poster" onClick={() => setPlaying(true)} aria-label={`Play video: ${title}`}>
        <img src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`} alt="" loading="lazy" />
        <span className="video-block__play" aria-hidden="true">
          <Play size={22} fill="currentColor" />
        </span>
      </button>
    )
  } else if (block.video_file) {
    frame = <video src={block.video_file} controls preload="metadata" />
  } else {
    frame = <div className="video-block__placeholder">Video unavailable</div>
  }

  return (
    <div className="video-block card">
      <div className="video-block__frame">{frame}</div>
      {block.title && <p className="video-block__title">{block.title}</p>}
    </div>
  )
}
