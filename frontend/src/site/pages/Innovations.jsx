import PageShell from '../components/PageShell.jsx'
import { ClosingBand, PageBanner, RichText, VideoPoster } from '../components/Blocks.jsx'
import { Img } from '../media.jsx'

/** Innovations (listing + detail): an index of all titles, then one article per innovation. */
export default function Innovations({ data }) {
  const c = data.collections || {}
  const items = c.innovations || []
  const slides = (c['project-slides'] || []).filter((s) => s.image)

  return (
    <PageShell data={data} className="innovations">
      <PageBanner
        title="Innovations"
        intro="Medical devices, diagnostics and digital health tools developed at CRTDH for low-resource settings."
      >
        {items.length > 0 && (
          <nav className="jump" aria-label="Innovations on this page">
            <ul>
              {items.map((it) => (
                <li key={it.id}>
                  <a href={`#innovation-${it.id}`}>{it.title}</a>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </PageBanner>

      {slides.length > 0 && (
        <section className="section section--surface" aria-labelledby="spotlight">
          <div className="wrap">
            <div className="section-head">
              <h2 id="spotlight">Project spotlight</h2>
            </div>
          </div>
          <div className="wrap">
            <ul className="spotlight">
              {slides.map((s) => (
                <li key={s.id}>
                  <figure>
                    <Img src={s.image} alt={s.image_alt || s.title || ''} ratio="1x1" figure sizes="(min-width: 768px) 22vw, 45vw" />
                    {s.title && <figcaption>{s.title}</figcaption>}
                  </figure>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {items.length > 0 && (
        <section className="section" aria-label="All innovations">
          <div className="wrap articles">
            {items.map((it) => {
              const imgs = (it.images || []).filter((im) => im.image)
              return (
                <article key={it.id} id={`innovation-${it.id}`} className={`article${imgs.length ? '' : ' article--text'}`}>
                  <div className="article__text">
                    <h2>{it.title}</h2>
                    <RichText html={it.body} className="mt-6" />
                    {it.video_url && <VideoPoster url={it.video_url} title={it.title} />}
                  </div>
                  {imgs.length > 0 && (
                    <div className={`article__media article__media--${Math.min(imgs.length, 4)}`}>
                      {imgs.slice(0, 4).map((im) => (
                        <figure key={im.id}>
                          <Img src={im.image} alt={im.image_alt || im.caption || it.title} ratio={null} contain sizes="(min-width: 768px) 30vw, 100vw" />
                          {im.caption && imgs.length > 1 && <figcaption>{im.caption}</figcaption>}
                        </figure>
                      ))}
                    </div>
                  )}
                </article>
              )
            })}
          </div>
        </section>
      )}
      <ClosingBand
        id="innovations-cta"
        surface
        title="Licence or co-develop a technology"
        text="Enterprises and health programmes can licence a CRTDH device or develop one further with the team."
        action="Talk to the centre"
      />
    </PageShell>
  )
}
