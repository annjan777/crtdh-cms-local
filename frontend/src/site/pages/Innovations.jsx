import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUpRight } from 'lucide-react'
import { YouTubeFacade, youtubeEmbedUrl } from '../components/ClickToLoad.jsx'
import { PageDataProvider } from '../api/data.jsx'
import RichText from '../components/RichText.jsx'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import Carousel from '../components/Carousel'
import { DataState } from '../components/StateBlock'
import { usePageMotion } from '../components/motion4.js'
import './Innovations.css'

const anchor = (t) => `technology-${t.id}`
const STATUS = { research: 'Research', prototype: 'Prototype', 'field-evaluation': 'Field evaluation', deployed: 'Deployed', commercialised: 'Commercialised' }
const Status = ({ t }) => (STATUS[t.status] ? <span className={`tech-status tech-status--${t.status}`}>{STATUS[t.status]}</span> : null)

/* Portfolio index: every technology as a row; on a pointer device the row's first photo previews beside the list. */
function PortfolioIndex({ items, all, cat, setCat, cats }) {
  const [hover, setHover] = useState(null)
  const preview = items.find((t) => t.id === hover)
  const previewImg = preview?.images?.[0]?.image
  return (
    <section className="tech-index" aria-labelledby="tech-index-title">
      <div className="container tech-index__grid">
        <div className="tech-index__aside">
          <span className="eyebrow">Portfolio</span>
          <h2 className="section-title" id="tech-index-title">{all.length} technologies, from the lab bench to the clinic</h2>
          <p className="tech-index__lead">Choose a technology to read how it works, what it is for and how far it has come.</p>
          <div className={`tech-index__preview${previewImg ? ' is-on' : ''}`} aria-hidden="true">
            {items.map((t) => t.images?.[0]?.image && (
              <img key={t.id} src={t.images[0].image} alt="" loading="lazy" className={t.id === hover ? 'is-current' : ''} />
            ))}
          </div>
        </div>
        <div>
        {cats.length > 1 && (
          <div className="tech-filter" role="toolbar" aria-label="Show technologies">
            {['All', ...cats].map((c) => (
              <button type="button" key={c} aria-pressed={cat === c} onClick={() => setCat(c)}>{c}</button>
            ))}
          </div>
        )}
        <ol className="tech-index__list" aria-live="polite">
          {items.map((t, k) => (
            <li key={t.id} data-rv style={{ '--d': `${Math.min(k, 8) * 50}ms` }}>
              <a
                href={`#${anchor(t)}`}
                className="tech-index__row"
                onMouseEnter={() => setHover(t.id)}
                onFocus={() => setHover(t.id)}
                onMouseLeave={() => setHover(null)}
                onBlur={() => setHover(null)}
              >
                <span className="tech-index__thumb">{t.images?.[0]?.image && <img src={t.images[0].image} alt="" loading="lazy" />}</span>
                <span className="tech-index__text">
                  <span className="tech-index__name">{t.title}</span>
                  {(t.summary || t.category || STATUS[t.status]) && (
                    <span className="tech-index__meta">
                      {t.category && <span className="tech-index__cat">{t.category}</span>}
                      <Status t={t} />
                      {t.summary && <span className="tech-index__sum">{t.summary}</span>}
                    </span>
                  )}
                </span>
                <ArrowRight className="tech-index__go" size={20} aria-hidden="true" />
              </a>
            </li>
          ))}
        </ol>
        </div>
      </div>
    </section>
  )
}

/* One technology: photos first (a large frame and the rest as a strip), then the write-up. Long write-ups open
   progressively; the full text is always in the page. */
function Technology({ t, flip }) {
  const imgs = t.images || []
  const [main, setMain] = useState(0)
  const [open, setOpen] = useState(false)
  const bodyRef = useRef(null)
  const [long, setLong] = useState(false)
  useEffect(() => {
    const el = bodyRef.current
    if (el) setLong(el.scrollHeight > 420)
    const onHash = () => { if (window.location.hash === `#${anchor(t)}`) setOpen(true) }
    onHash()
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [t])
  return (
    <article className={`tech${flip ? ' tech--flip' : ''}${imgs.length ? '' : ' tech--text'}`} id={anchor(t)} aria-labelledby={`${anchor(t)}-h`}>
      {imgs.length > 0 && (
        <div className="tech__media">
          <figure className="tech__frame zoom" data-rv="mask">
            <img src={imgs[main].image} alt={imgs[main].caption || t.title} loading="lazy" />
            {imgs[main].caption && <figcaption>{imgs[main].caption}</figcaption>}
          </figure>
          {imgs.length > 1 && (
            <div className="tech__strip" role="group" aria-label={`${t.title}: photos`}>
              {imgs.map((im, k) => (
                <button type="button" key={im.id} className={k === main ? 'is-current' : ''} aria-pressed={k === main} onClick={() => setMain(k)}>
                  <img src={im.image} alt={im.caption || `${t.title}, photo ${k + 1}`} loading="lazy" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="tech__copy" data-rv>
        {(t.category || STATUS[t.status]) && (
          <p className="tech__tags">{t.category && <span className="tech-index__cat">{t.category}</span>}<Status t={t} /></p>
        )}
        <h2 className="tech__title" id={`${anchor(t)}-h`}>{t.title}</h2>
        {t.summary && <p className="tech__summary">{t.summary}</p>}
        {t.body && (
          <div className={`tech__body${long && !open ? ' is-clamped' : ''}`} ref={bodyRef} id={`${anchor(t)}-body`}>
            <RichText html={t.body} className="rich-text" />
          </div>
        )}
        {long && (
          <button type="button" className="tech__more" aria-expanded={open} aria-controls={`${anchor(t)}-body`} onClick={() => setOpen((v) => !v)}>
            {open ? 'Show less' : 'Read the full write-up'}
          </button>
        )}
        {youtubeEmbedUrl(t.video_url) && (
          <div className="tech__video"><YouTubeFacade url={t.video_url} title={t.title} /></div>
        )}
        <a className="tech__ask" href="/contact/">Ask about this technology <ArrowUpRight size={16} aria-hidden="true" /></a>
      </div>
    </article>
  )
}

function InnovationsView() {
  const { data: innovations, loading, error } = useApi(() => fetchList('/innovations/'), [], [])
  const { data: projectSlides, loading: slidesLoading } = useApi(() => fetchList('/project-slides/'), [], [])
  const ref = useRef(null)
  const [cat, setCat] = useState('All')
  usePageMotion(ref, [innovations, projectSlides])
  const cats = [...new Set((innovations || []).map((t) => (t.category || '').trim()).filter(Boolean))]
  const heroImg = (innovations || []).find((t) => /covirap/i.test(t.title) && t.images?.length)?.images?.[0]?.image
    || (innovations || []).find((t) => t.images?.length)?.images?.[0]?.image

  return (
    <div ref={ref} className="tech-page">
      <PageHero
        page="innovations"
        eyebrow="Innovations"
        title="Our technology portfolio"
        description="Medical devices, diagnostics and digital health tools developed at CRTDH for real-world, resource-constrained settings."
        image={heroImg}
      />

      <section data-block="innovations.list">
        <DataState
          loading={loading}
          error={error}
          data={innovations}
          emptyProps={{ title: 'Innovations coming soon', message: 'Check back for device and diagnostic write-ups.' }}
        >
          {(items) => (
            <>
              <PortfolioIndex items={cat === 'All' ? items : items.filter((t) => (t.category || '').trim() === cat)} all={items} cat={cat} setCat={setCat} cats={cats} />
              {!slidesLoading && projectSlides && projectSlides.length > 0 && (
                <section data-block="innovations.spotlight" className="tech-spot" aria-labelledby="tech-spot-title">
                  <div className="container tech-spot__grid">
                    <div className="tech-spot__copy" data-rv>
                      <span className="eyebrow eyebrow--on-dark">Spotlight</span>
                      <h2 className="tech-spot__title" id="tech-spot-title">Project spotlight</h2>
                      <ul className="tech-spot__parts">{projectSlides.filter((s) => s.title).map((s) => <li key={s.id}>{s.title}</li>)}</ul>
                    </div>
                    <div className="tech-spot__stage" data-rv="wipe">
                      <Carousel
                        items={projectSlides}
                        ariaLabel="Project highlight carousel"
                        renderItem={(slide) => (
                          <div className="project-slide">
                            <img src={slide.image} alt={slide.title || ''} />
                            {slide.title && <div className="project-slide__caption">{slide.title}</div>}
                          </div>
                        )}
                      />
                    </div>
                  </div>
                </section>
              )}
              <div className="container tech-list">
                {items.map((t, k) => (
                  <div key={t.id} hidden={cat !== 'All' && (t.category || '').trim() !== cat}>
                    <Technology t={t} flip={k % 2 === 1} />
                  </div>
                ))}
              </div>
            </>
          )}
        </DataState>
      </section>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Innovations({ data }) {
  return (
    <PageDataProvider data={data}>
      <InnovationsView />
    </PageDataProvider>
  )
}
