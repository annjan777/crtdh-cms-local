import './VideoBlock.css'

function toEmbedUrl(youtubeUrl) {
  try {
    const url = new URL(youtubeUrl)
    if (url.hostname.includes('youtu.be')) {
      return `https://www.youtube.com/embed/${url.pathname.slice(1)}`
    }
    const videoId = url.searchParams.get('v')
    if (videoId) return `https://www.youtube.com/embed/${videoId}`
    return youtubeUrl
  } catch {
    return youtubeUrl
  }
}

export default function VideoBlock({ block }) {
  if (!block) return null
  return (
    <div className="video-block card">
      <div className="video-block__frame">
        {block.youtube_url ? (
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
