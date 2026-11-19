import { youtubeId } from '../util.js'
import './VideoBlock.css'

function toEmbedUrl(youtubeUrl) {
  const id = youtubeId(youtubeUrl)
  return id && /^[\w-]{6,20}$/.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : null
}

export default function VideoBlock({ block }) {
  if (!block) return null
  return (
    <div className="video-block card">
      <div className="video-block__frame">
        {toEmbedUrl(block.youtube_url) ? (
          <iframe
            src={toEmbedUrl(block.youtube_url)}
            title={block.title || 'Video'}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : block.video_file ? (
          <video src={block.video_file} controls preload="metadata" />
        ) : (
          <div className="video-block__placeholder">🎬 Video unavailable</div>
        )}
      </div>
      {block.title && <p className="video-block__title">{block.title}</p>}
    </div>
  )
}
