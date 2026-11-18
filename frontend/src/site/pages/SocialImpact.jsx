import PageShell from '../components/PageShell.jsx'
import { Gallery, PageBanner, VideoPoster } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'
import { SOCIAL_IMPACT_TEXT } from '../content.js'
import { blocksFor, uniqueItems } from '../util.js'

const INTRO = 'Health camps, rural clinics and outreach programmes bringing CRTDH innovations to the people who need them most.'

/** Social impact (detail pattern): the story in one reading column, then the outreach photographs. */
export default function SocialImpact({ data }) {
  const c = data.collections || {}
  const home = data.singletons?.['home-page'] || {}
  const blocks = blocksFor(c['image-grid-blocks'], 'social-impact')
  const videos = dedupeVideos((c['video-blocks'] || []).filter((v) => v.page === 'social-impact'))
  return (
    <PageShell data={data} className="impact">
      <PageBanner title="Social impact" intro={INTRO} image={home.women_image_1} />
      <section className="section" aria-labelledby="impact-story">
        <div className="wrap split">
          <div className="split__main">
            <h2 id="impact-story">E-health clinics and local livelihoods</h2>
            <div className="prose mt-6">
              {SOCIAL_IMPACT_TEXT.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </div>
          {home.women_image_2 && (
            <figure className="split__side">
              <Img src={home.women_image_2} alt="" ratio="4x5" sizes="(min-width: 768px) 30vw, 100vw" />
            </figure>
          )}
        </div>
      </section>
      {blocks.map((b) => (
        <section className="section section--surface" key={b.id} id={b.anchor_slug || undefined} aria-labelledby={`block-${b.id}`}>
          <div className="wrap">
            <div className="section-head">
              <h2 id={`block-${b.id}`}>{b.section_title}</h2>
              {b.intro && b.intro.trim() !== INTRO && <p>{b.intro}</p>}
            </div>
            <Gallery items={uniqueItems(b.items)} title={b.section_title} />
          </div>
        </section>
      ))}
      {videos.length > 0 && (
        <section className="section" aria-labelledby="impact-videos">
          <div className="wrap">
            <div className="section-head">
              <h2 id="impact-videos">Community stories</h2>
            </div>
            <div className="videos">
              {videos.map((v) => (
                <VideoPoster key={v.id} url={v.youtube_url} title={v.title} />
              ))}
            </div>
          </div>
        </section>
      )}
    </PageShell>
  )
}

export function dedupeVideos(list) {
  const seen = new Set()
  return list.filter((v) => {
    const k = (v.title || '').trim() || v.id
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
}
