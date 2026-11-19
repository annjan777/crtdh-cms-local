import PageShell from '../components/PageShell.jsx'
import { Gallery, PageBanner, VideoPoster } from '../components/Blocks.jsx'
import { COVID_TEXT } from '../content.js'
import { blocksFor, uniqueItems } from '../util.js'
import { dedupeVideos } from './SocialImpact.jsx'

/** Covid-19 response (detail pattern): the account in one reading column, photographs, videos. */
export default function Covid19({ data }) {
  const c = data.collections || {}
  const blocks = blocksFor(c['image-grid-blocks'], 'covid-19')
  const videos = dedupeVideos((c['video-blocks'] || []).filter((v) => v.page === 'covid-19'))
  const items = uniqueItems(blocks.flatMap((b) => b.items || []))
  const lead = blocks[0]
  return (
    <PageShell data={data} className="covid">
      <PageBanner
        title="Covid-19 response"
        intro={lead?.intro || 'Diagnostics, training and community relief undertaken by CRTDH during the Covid-19 pandemic.'}
      />
      <section className="section" aria-labelledby="covid-story" id={lead?.anchor_slug || undefined}>
        <div className="wrap">
          <h2 id="covid-story">{lead?.section_title || 'Combating the pandemic'}</h2>
          <div className="prose mt-6">
            {COVID_TEXT.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>
      </section>
      {items.length > 0 && (
        <section className="section section--surface" aria-labelledby="covid-photos">
          <div className="wrap">
            <div className="section-head">
              <h2 id="covid-photos">In the field</h2>
            </div>
            <Gallery items={items} title="Covid-19 response" columns={items.length === 4 ? 2 : 3} />
          </div>
        </section>
      )}
      {videos.length > 0 && (
        <section className="section" aria-labelledby="covid-videos">
          <div className="wrap">
            <div className="section-head">
              <h2 id="covid-videos">Response in action</h2>
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
