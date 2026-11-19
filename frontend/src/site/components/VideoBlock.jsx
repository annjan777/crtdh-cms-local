import { YouTubeFacade, youtubeEmbedUrl } from './ClickToLoad.jsx'
import './VideoBlock.css'

export default function VideoBlock({ block }) {
  if (!block) return null
  return (
    <div className="video-block card">
      <div className="video-block__frame">
        {youtubeEmbedUrl(block.youtube_url) ? (
          <YouTubeFacade url={block.youtube_url} title={block.title} />
        ) : block.video_file ? (
          <video src={block.video_file} controls preload="metadata" />
        ) : (
          <div className="video-block__placeholder">Video unavailable</div>
        )}
      </div>
      {block.title && <p className="video-block__title">{block.title}</p>}
    </div>
  )
}
