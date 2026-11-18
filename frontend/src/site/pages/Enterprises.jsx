import PageShell from '../components/PageShell.jsx'
import { GridBlock, PageBanner, VideoPoster } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'
import { blocksFor } from '../util.js'

/** Enterprises (listing): the cluster directory, the engagement story and the training gallery. */
export default function Enterprises({ data }) {
  const c = data.collections || {}
  const home = data.singletons?.['home-page'] || {}
  const enterprises = c.enterprises || []
  const blocks = blocksFor(c['image-grid-blocks'], 'enterprises')
  const videos = (c['video-blocks'] || []).filter((v) => v.page === 'enterprises')
  return (
    <PageShell data={data} className="enterprises">
      <PageBanner
        title="Enterprises"
        intro="MSMEs and startups engaged with CRTDH, from medtech startups scaling manufacturing to rural livelihood ventures."
      />
      {(home.enterprises_text || home.msme_map_image) && (
        <section className="section" aria-labelledby="ent-engagement">
          <div className="wrap split">
            <div className="split__main">
              <h2 id="ent-engagement">Enterprise engagement</h2>
              {home.enterprises_text && <p className="mt-6 prose">{home.enterprises_text}</p>}
            </div>
            {home.msme_map_image && (
              <figure className="split__side">
                <Img src={home.msme_map_image} alt={home.msme_caption || 'Map of the MSME cluster'} ratio={null} contain sizes="(min-width: 768px) 32vw, 100vw" />
                {home.msme_caption && <figcaption>{home.msme_caption}</figcaption>}
              </figure>
            )}
          </div>
        </section>
      )}
      {enterprises.length > 0 && (
        <section className="section section--surface" aria-labelledby="ent-directory">
          <div className="wrap">
            <div className="section-head">
              <h2 id="ent-directory">The enterprise cluster</h2>
              <p>{enterprises.length} enterprises work with the centre.</p>
            </div>
            <ul className="logos">
              {enterprises.map((e) => (
                <li key={e.id} className="logo-card card">
                  <div className="logo-card__mark">
                    {e.logo ? <img src={e.logo} alt="" loading="lazy" /> : <span aria-hidden="true">{initials(e.name)}</span>}
                  </div>
                  <p className="logo-card__name">{e.name}</p>
                  {e.subtitle && <p className="logo-card__sub soft">{e.subtitle.replace(/^\((.*)\)$/, '$1')}</p>}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
      {blocks.length > 0 && (
        <section className="section" aria-label="Demonstration and training">
          <div className="wrap">
            {blocks.map((b) => (
              <GridBlock key={b.id} block={b} />
            ))}
          </div>
        </section>
      )}
      {videos.length > 0 && (
        <section className="section section--surface" aria-labelledby="ent-videos">
          <div className="wrap">
            <div className="section-head">
              <h2 id="ent-videos">Enterprise stories</h2>
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

function initials(name) {
  return String(name || '')
    .replace(/^M\/s\.?\s*/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
}
