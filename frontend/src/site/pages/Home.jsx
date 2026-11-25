import { useEffect, useMemo, useRef, useState } from 'react'
import { PageDataProvider } from '../api/data.jsx'
import { safeHref } from '../util.js'
import { MapFacade, directionsUrl } from '../components/ClickToLoad.jsx'
import SiteLink from '../link.jsx'
import { Link } from '../router.jsx'
import { ArrowRight, Cpu, FlaskConical, Users, Microscope, Handshake, GraduationCap, Pause, Play } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchList, fetchOne } from '../api/client'
import VideoBlock from '../components/VideoBlock'
import { useParallax, useReveals, prefersReducedMotion } from '../components/motion4.js'
import './Home.css'

// The editor's focus point for a hero photo (CMS "click the part to keep in view"): a CSS object-position
// such as "30% 45%" or "right top". The CMS validates it; anything else falls back to the stylesheet's default.
const FOCUS_RE = /^((left|center|right|top|bottom) (left|center|right|top|bottom)|\d{1,3}(\.\d)?% \d{1,3}(\.\d)?%)$/
function focusStyle(position) {
  return position && position !== 'center center' && FOCUS_RE.test(position) ? { objectPosition: position } : undefined
}

// The three pathways under the hero. The CMS has no fields for them yet (see docs: proposed
// HomePage.pathway_*), so the wording lives here, next to the links it describes.
const PATHWAY_ICONS = { technology: Cpu, research: FlaskConical, rural: Users, facilities: Microscope, industry: Handshake, training: GraduationCap }
// Built-in wording, used where the CMS pathway fields (home-page pathway_N_*) are empty.
const PATHWAYS = [
  { title: 'Technology', text: 'Indigenous, affordable and ready-to-deploy healthcare solutions.', to: '/innovations', Icon: Cpu },
  { title: 'Research Translation', text: 'From lab innovation to real-world healthcare technologies.', to: '/enterprises', Icon: FlaskConical },
  { title: 'Rural Impact', text: 'Taking healthcare innovation to last-mile and resource-limited settings.', to: '/social-impact', Icon: Users },
]

const firstSentence = (t) => {
  const m = String(t || '').trim().match(/^(.+?[.!?])(\s|$)/s)
  return m ? m[1] : String(t || '')
}

function Arrow({ size = 18 }) {
  return <ArrowRight size={size} aria-hidden="true" strokeWidth={1.8} />
}

/* ---------------------------------------------------------------- A + B: hero */
function Hero({ slides }) {
  const [i, setI] = useState(0)
  const [paused, setPaused] = useState(false)
  useEffect(() => { if (prefersReducedMotion()) setPaused(true) }, [])
  useEffect(() => {
    if (paused || slides.length < 2) return undefined
    const t = setTimeout(() => setI((n) => (n + 1) % slides.length), 7000)
    return () => clearTimeout(t)
  }, [i, paused, slides.length])
  const s = slides[i] || slides[0]
  if (!s) return null
  const line2 = [s.highlight_heading, s.heading_end].filter(Boolean).join(' ')
  return (
    <section data-block="home.hero" className="h4-hero" aria-roledescription="carousel" aria-label="CRTDH at work">
      <div className="h4-hero__media" data-px="0.22" data-px-mode="top">
        {slides.map((sl, n) => (
          <div key={sl.id ?? n} className={`h4-hero__slide ${n === i ? 'is-on' : ''}`} aria-hidden={n !== i}>
            <img src={sl.image} alt="" style={focusStyle(sl.image_position)} fetchPriority={n === 0 ? 'high' : undefined} loading={n === 0 ? 'eager' : 'lazy'} />
          </div>
        ))}
      </div>
      <div className="h4-hero__shade" aria-hidden="true" />
      <div className="h4-hero__inner">
        <div className="h4-hero__copy" key={s.id ?? i}>
          {s.eyebrow && <p className="h4-hero__eyebrow"><span aria-hidden="true" />{s.eyebrow}</p>}
          <h1 className="h4-hero__title">
            <span className="h4-line"><span>{s.heading}</span></span>
            {line2 && <span className="h4-line"><span>{line2}</span></span>}
          </h1>
          {s.description && <p className="h4-hero__lede">{s.description}</p>}
          <div className="h4-hero__actions">
            {s.primary_button_label && s.primary_button_link && (
              <SiteLink to={s.primary_button_link} className="h4-pill">{s.primary_button_label} <Arrow /></SiteLink>
            )}
            {s.secondary_button_label && s.secondary_button_link && (
              <SiteLink to={s.secondary_button_link} className="h4-hero__second">{s.secondary_button_label}</SiteLink>
            )}
          </div>
        </div>
        {slides.length > 1 && (
          <div className="h4-hero__controls">
            <div className="h4-bars" role="group" aria-label="Choose photo">
              {slides.map((sl, n) => (
                <button key={sl.id ?? n} type="button" aria-label={`Photo ${n + 1} of ${slides.length}`}
                  aria-current={n === i ? 'true' : undefined} onClick={() => setI(n)}
                  className={n === i && !paused ? 'is-running' : undefined} />
              ))}
            </div>
            <button type="button" className="h4-hero__pause" onClick={() => setPaused((p) => !p)}
              aria-label={paused ? 'Play photos' : 'Pause photos'}>
              {paused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
            </button>
          </div>
        )}
      </div>
      {/* C: the organic edge into the page */}
      <svg className="h4-hero__wave" viewBox="0 0 1600 200" preserveAspectRatio="none" aria-hidden="true">
        <path className="h4-wave-sage" d="M0 70 C 120 130 250 156 520 132 L 520 200 L 0 200 Z" />
        <path className="h4-wave-ivory" d="M0 142 C 220 118 470 66 700 72 C 900 78 960 196 1110 200 C 1290 204 1450 168 1600 146 L 1600 200 L 0 200 Z" />
      </svg>
    </section>
  )
}

/* ---------------------------------------------------------------- D: pathways */
function Pathways({ home }) {
  const items = PATHWAYS.map((d, k) => {
    const n = k + 1
    return {
      title: home?.[`pathway_${n}_title`] || d.title,
      text: home?.[`pathway_${n}_text`] || d.text,
      to: home?.[`pathway_${n}_link`] || d.to,
      Icon: PATHWAY_ICONS[home?.[`pathway_${n}_icon`]] || d.Icon,
    }
  })
  return (
    <section className="h4-paths" aria-label="What CRTDH does" data-block="home.pathways">
      <div className="h4-wrap h4-paths__row">
        {items.map(({ title, text, to, Icon }, n) => (
          <SiteLink key={n} to={to} className="h4-path" data-rv style={{ '--d': `${n * 120}ms` }}>
            <span className="h4-path__icon"><Icon size={30} strokeWidth={1.6} aria-hidden="true" /></span>
            <span className="h4-path__body">
              <span className="h4-path__title">{title}</span>
              <span className="h4-path__text">{text}</span>
            </span>
            <span className="h4-circle" aria-hidden="true"><Arrow size={16} /></span>
          </SiteLink>
        ))}
      </div>
    </section>
  )
}

/* ---------------------------------------------------------------- E: gallery + latest updates */
function fmtDate(iso) {
  const d = new Date(`${iso}T00:00:00`)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function Showcase({ gallery, news, eventThumb }) {
  const big = gallery[0]
  const panel = gallery[1] || gallery[0]
  // Every published item is listed (CMS order); the first three carry a photo, the rest are text rows.
  const items = news
  if (!big && !items.length) return null
  return (
    <section className="h4-show">
      <div className="h4-show__compo" data-rv>
        {big && (
          <div className="h4-show__big">
            <img src={big.image} alt={big.caption || ''} loading="lazy" data-px="0.08" />
          </div>
        )}
        {panel && (
          <Link to="/media" className="h4-show__panel" aria-label="Open the gallery">
            <img src={panel.image} alt="" loading="lazy" />
            <span className="h4-show__panel-label">Gallery <span className="h4-circle h4-circle--light"><Arrow size={16} /></span></span>
          </Link>
        )}
        <svg className="h4-show__wave" viewBox="0 0 1000 120" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 0 L 1000 0 L 1000 52 C 900 26 800 10 700 22 C 600 34 520 98 380 104 C 250 110 120 70 0 30 Z" />
        </svg>
      </div>
      {items.length > 0 && (
        <div data-block="home.news" className="h4-show__news" data-rv>
          <div className="h4-show__head">
            <h2 className="h4-rule-title"><span aria-hidden="true" />Latest Updates</h2>
            <Link to="/media" className="h4-textlink">View All <Arrow size={16} /></Link>
          </div>
          <ul className="h4-updates">
            {items.map((n, k) => {
              const { thumb: t, date } = eventThumb(n.link_url)
              const thumb = k < 3 ? t : null
              return (
                <li key={n.id}>
                  <SiteLink to={n.link_url || '/media'} className={`h4-update${k < 3 ? '' : ' h4-update--text'}`}>
                    {k < 3 && <span className="h4-update__thumb">{thumb ? <img src={thumb} alt="" loading="lazy" /> : null}</span>}
                    <span className="h4-update__body">
                      <span className="h4-update__text">{n.text}</span>
                      {date && <time className="h4-update__date" dateTime={date}>{fmtDate(date)}</time>}
                    </span>
                  </SiteLink>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </section>
  )
}

/* ---------------------------------------------------------------- figures: counts from the CMS lists */
function Figures({ items }) {
  return (
    <section className="h4-figs" aria-label="CRTDH in numbers">
      <dl className="h4-wrap h4-figs__row">
        {items.map((f, k) => (
          <div className="h4-fig" key={f.label} data-rv style={{ '--d': `${k * 90}ms` }}>
            <dt className="h4-fig__label">{f.label}</dt>
            <dd className="h4-fig__value">{f.value}+</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

/* ---------------------------------------------------------------- F..J: the rest of the CMS home content */
function Objective({ home }) {
  if (!home.objective_text && !home.membership_heading && !home.membership_pdf) return null
  return (
    <section className="h4-section">
      <div className="h4-wrap h4-split">
        {home.objective_text && (
          <div data-block="home.objective" className="h4-objective" data-rv>
            <p className="h4-statement">{firstSentence(home.objective_text)}</p>
            <p className="h4-body">{home.objective_text.slice(firstSentence(home.objective_text).length).trim()}</p>
            <Link to="/about" className="h4-textlink">About CRTDH <Arrow size={16} /></Link>
          </div>
        )}
        {(home.membership_heading || home.membership_pdf) && (
          <div data-block="home.membership" className="h4-member" data-rv style={{ '--d': '120ms' }}>
            <h2 className="h4-h3">{home.membership_heading || 'Annual Membership for MSME / Startup'}</h2>
            <p className="h4-body">R&amp;D support, the pilot plant, validation and licensing for MSMEs and startups.</p>
            {home.membership_pdf && (
              <a className="h4-pill h4-pill--forest" href={safeHref(home.membership_pdf)} target="_blank" rel="noreferrer">
                Membership details <Arrow />
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

function Enterprises({ home }) {
  if (!home.enterprises_text) return null
  const imgs = [home.enterprises_image_1, home.enterprises_image_2].filter(Boolean)
  return (
    <section data-block="home.enterprises" className="h4-section h4-ent">
      <div className="h4-wrap h4-split h4-split--media">
        <div className="h4-ent__media" data-rv>
          {imgs[0] && <div className="h4-ent__a"><img src={imgs[0]} alt="" loading="lazy" /></div>}
          {imgs[1] && <div className="h4-ent__b"><img src={imgs[1]} alt="" loading="lazy" /></div>}
        </div>
        <div className="h4-stack" data-rv style={{ '--d': '120ms' }}>
          <h2 className="h4-h2">From innovation to manufacturing</h2>
          <p className="h4-body">{home.enterprises_text}</p>
          <Link to="/enterprises" className="h4-textlink">Work with CRTDH <Arrow size={16} /></Link>
        </div>
      </div>
    </section>
  )
}

function Rural({ home }) {
  if (!home.women_text_1) return null
  return (
    <section data-block="home.rural" className="h4-band">
      <svg className="h4-band__edge h4-band__edge--top" viewBox="0 0 1600 120" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 0 L1600 0 L1600 40 C 1380 110 1120 120 860 80 C 600 40 320 30 0 90 Z" />
      </svg>
      <div className="h4-wrap h4-split h4-split--media h4-band__inner">
        <div className="h4-stack" data-rv>
          <h2 className="h4-h2">E-health clinics where there was no clinic</h2>
          <p className="h4-body">{home.women_text_1}</p>
          <Link to="/social-impact" className="h4-textlink h4-textlink--light">Read the story <Arrow size={16} /></Link>
        </div>
        <div className="h4-band__media" data-rv style={{ '--d': '120ms' }}>
          {home.women_image_2 && <div className="h4-band__a"><img src={home.women_image_2} alt="" loading="lazy" data-px="0.06" /></div>}
          {home.women_image_1 && <div className="h4-band__b"><img src={home.women_image_1} alt="" loading="lazy" /></div>}
        </div>
      </div>
      <svg className="h4-band__edge h4-band__edge--bottom" viewBox="0 0 1600 120" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 120 L0 60 C 260 0 560 10 820 52 C 1080 94 1340 100 1600 40 L1600 120 Z" />
      </svg>
    </section>
  )
}

function Facilities({ home }) {
  const cards = [
    { title: home.facility_card_1_title, image: home.facility_card_1_image, link: home.facility_card_1_link },
    { title: home.facility_card_2_title, image: home.facility_card_2_image, link: home.facility_card_2_link },
    { title: home.facility_card_3_title, image: home.facility_card_3_image, link: home.facility_card_3_link },
  ].filter((c) => c.title || c.image)
  const hasVideos = home.chintan_shivir_youtube_id || home.viksit_bharat_youtube_id
  return (
    <section data-block="home.facilities" className="h4-section">
      <div className="h4-wrap">
        <div className="h4-head" data-rv>
          <h2 className="h4-h2">Pilot plant and laboratories</h2>
          <Link to="/facilities" className="h4-textlink">All facilities <Arrow size={16} /></Link>
        </div>
        {home.location_description && <p className="h4-lead" data-rv>{home.location_description}.</p>}
        <ul className="h4-fac">
          {cards.map((c, n) => {
            const inner = (
              <>
                <span className="h4-fac__img">{c.image && <img src={c.image} alt="" loading="lazy" />}</span>
                <span className="h4-fac__title">{c.title}</span>
              </>
            )
            return (
              <li key={c.title || n} data-rv style={{ '--d': `${n * 100}ms` }}>
                {c.link ? <SiteLink to={c.link} className="h4-fac__link">{inner}</SiteLink> : <span className="h4-fac__link">{inner}</span>}
              </li>
            )
          })}
        </ul>
        {hasVideos && (
          <div data-block="home.videos" className="h4-videos" data-rv>
            <h3 className="h4-h3">See CRTDH in action</h3>
            <div className="h4-videos__row">
              {home.chintan_shivir_youtube_id && (
                <VideoBlock block={{ title: 'Chintan Shivir', youtube_url: `https://www.youtube.com/watch?v=${home.chintan_shivir_youtube_id}` }} />
              )}
              {home.viksit_bharat_youtube_id && (
                <VideoBlock block={{ title: 'Viksit Bharat Abhiyan', youtube_url: `https://www.youtube.com/watch?v=${home.viksit_bharat_youtube_id}` }} />
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function Visit({ home, siteSettings }) {
  if (!siteSettings?.map_embed_url) return null
  return (
    <section data-block="home.visit" className="h4-section h4-section--alt">
      <div className="h4-wrap h4-split">
        <div className="h4-stack" data-rv>
          <h2 className="h4-h2">Visit CRTDH</h2>
          <p className="h4-lead">{home?.location_address || siteSettings.address}</p>
          <div className="h4-actions">
            <a className="h4-pill h4-pill--forest" href={directionsUrl(siteSettings.address || home?.location_address)} target="_blank" rel="noopener noreferrer">Get directions <Arrow /></a>
            <Link to="/contact" className="h4-textlink">Contact us <Arrow size={16} /></Link>
          </div>
        </div>
        <div className="h4-map" data-rv style={{ '--d': '120ms' }}>
          <MapFacade src={siteSettings.map_embed_url} address={siteSettings.address} />
        </div>
      </div>
    </section>
  )
}

function HomeView() {
  const { data: slidesRaw } = useApi(() => fetchList('/hero-slides/'), [], [])
  const { data: news } = useApi(() => fetchList('/news-items/'), [], [])
  const { data: home } = useApi(() => fetchOne('/home-page/'), [], null)
  const { data: siteSettings } = useApi(() => fetchOne('/site-settings/'), [], null)
  const { data: gallery } = useApi(() => fetchList('/gallery-images/'), [], [])
  const { data: events } = useApi(() => fetchList('/media-events/'), [], [])
  const { data: eventImages } = useApi(() => fetchList('/media-event-images/'), [], [])
  const { data: innovations } = useApi(() => fetchList('/innovations/'), [], [])
  const { data: enterprises } = useApi(() => fetchList('/enterprises/'), [], [])
  const { data: team } = useApi(() => fetchList('/team-members/'), [], [])
  // Counted from the CMS lists, as before; the DSIR figure is the one fixed number.
  const figures = [
    { label: 'Innovations developed', value: innovations?.length ?? 0 },
    { label: 'Enterprises incubated', value: enterprises?.length ?? 0 },
    { label: 'Researchers & staff', value: team?.length ?? 0 },
    { label: 'Years sponsored by DSIR', value: 8 },
  ]
  const slides = useMemo(() => (slidesRaw || []).filter((s) => s.image), [slidesRaw])

  // News items link to /media#<event slug>; use that event's first photo as the thumbnail.
  const eventThumb = useMemo(() => {
    const bySlug = new Map((events || []).map((e) => [e.slug, e]))
    const first = new Map()
    ;(eventImages || []).forEach((im) => { if (!first.has(im.event)) first.set(im.event, im.image) })
    // A news item that links to a gallery event ("/media#slug") borrows that event's first photo and date.
    return (url) => {
      const m = String(url || '').match(/#([\w-]+)$/)
      const ev = m ? bySlug.get(m[1]) : null
      return ev ? { thumb: first.get(ev.id) || null, date: ev.event_date || null } : { thumb: null, date: null }
    }
  }, [events, eventImages])

  const ref = useRef(null)
  useReveals(ref, [home, slides.length])
  useParallax(ref, [home, slides.length])

  return (
    <div className="v4 h4" ref={ref}>
      <Hero slides={slides} />
      <Pathways home={home} />
      <Showcase gallery={gallery || []} news={news || []} eventThumb={eventThumb} />
      <Figures items={figures} />
      {home && (
        <>
          <Objective home={home} />
          <Enterprises home={home} />
          <Rural home={home} />
          <Facilities home={home} />
        </>
      )}
      <Visit home={home} siteSettings={siteSettings} />
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Home({ data }) {
  return (
    <PageDataProvider data={data}>
      <HomeView />
    </PageDataProvider>
  )
}
