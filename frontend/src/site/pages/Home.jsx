import PageShell from '../components/PageShell.jsx'
import HeroPrints from '../components/HeroPrints.jsx'
import { VideoPoster, eventPhotoFor } from '../components/Blocks.jsx'
import SiteLink, { PlainLink } from '../link.jsx'
import { Img } from '../media.jsx'
import { visible } from '../util.js'

/**
 * Home (persuasive mode). Wireframe PLAN WS2.2: hero → proof → our work → news → visit.
 * Audience: industry partners, clinicians and health programmes; primary action "Work with CRTDH".
 */
export default function Home({ data }) {
  const s = data.singletons || {}
  const c = data.collections || {}
  const home = s['home-page'] || {}
  const settings = s['site-settings'] || {}
  const slides = visible(c['hero-slides'])
  const lead = slides[0] || {}
  const headline = [lead.heading, lead.highlight_heading, lead.heading_end].filter(Boolean).join(' ')

  return (
    <PageShell data={data} className="home">
      <section className="hero on-navy" aria-labelledby="hero-title">
        <div className="wrap hero__grid">
          <div className="hero__text">
            <h1 id="hero-title">{headline || 'Common Research and Technology Development Hub'}</h1>
            {lead.description && <p className="hero__line">{lead.description}</p>}
            <div className="actions">
              <SiteLink to="/services/" className="btn btn--primary">Work with CRTDH</SiteLink>
              <SiteLink to="/innovations/" className="btn btn--secondary">See our innovations</SiteLink>
            </div>
            <Figures items={homeFigures(c)} />
          </div>
          {slides.length > 0 && <HeroPrints slides={slides} />}
        </div>
      </section>

      <Proof enterprises={c.enterprises} products={c.products} />
      <Work innovations={c.innovations} />
      <Manufacturing home={home} equipment={c.equipment} />
      <Community home={home} />
      <News items={c['news-items']} documents={c.documents} events={c['media-events']} home={home} />
      <Visit home={home} settings={settings} />
    </PageShell>
  )
}

// Years the centre has been sponsored by DSIR, as the old site stated it (owner decision D10, 19 Nov 2026).
// A fixed figure, not computed: change it here when the centre's sponsorship statement changes.
export const DSIR_YEARS = 8

/** The figures strip from the old Home, computed from the published content like the old page did. */
export function homeFigures(c) {
  return [
    { value: visible(c.innovations).length, label: 'Innovations developed' },
    { value: visible(c.enterprises).length, label: 'Enterprises incubated' },
    { value: DSIR_YEARS, label: 'Years sponsored by DSIR' },
  ].filter((f) => f.value > 0)
}

/** A quiet typographic row (DESIGN.md: display figures in Fraunces; no cards, icons or counters). */
function Figures({ items }) {
  if (!items.length) return null
  return (
    <dl className="hero__figures" aria-label="CRTDH in figures">
      {items.map((f) => (
        <div key={f.label} className="hero__figure">
          <dt>{f.label}</dt>
          <dd>{f.value}+</dd>
        </div>
      ))}
    </dl>
  )
}

/** Proof: the enterprises and commercial partners the centre works with, as plain names. */
function Proof({ enterprises = [], products = [] }) {
  const partners = []
  for (const p of products) {
    for (const pt of p.partners || []) partners.push({ key: `${p.id}-${pt.id}`, name: pt.name, product: p.name })
  }
  if (!enterprises.length && !partners.length) return null
  return (
    <section className="section proof" aria-labelledby="proof-title">
      <div className="wrap grid12">
        <div className="proof__head">
          <h2 id="proof-title">Who builds with us</h2>
          <p className="soft">
            {enterprises.length} enterprises engaged with the centre
            {partners.length > 0 && `, and the partners taking ${products.length} of its products to market`}.
          </p>
          <SiteLink to="/enterprises/" className="text-link proof__all">All enterprises</SiteLink>
          {partners.length > 0 && (
            <dl className="names names--partners">
              <dt className="soft">Products and their partners</dt>
              {products
                .filter((p) => (p.partners || []).length)
                .map((p) => (
                  <dd key={p.id}>
                    <strong>{p.name}</strong>
                    <span className="soft"> with {p.partners.map((pt) => pt.name).join(', ')}</span>
                  </dd>
                ))}
            </dl>
          )}
        </div>
        <div className="proof__names">
          {enterprises.length > 0 && (
            <ul className="names" aria-label="Enterprises engaged">
              {enterprises.map((e) => (
                <li key={e.id}>{e.name}</li>
              ))}
            </ul>
          )}
          {enterprises.length > 8 && (
            <SiteLink to="/enterprises/" className="text-link proof__more">All {enterprises.length} enterprises</SiteLink>
          )}
        </div>
      </div>
    </section>
  )
}

/** Our work: heading cell, one wide print and one upright, then a row of four (layout in pages.css). */
function Work({ innovations = [] }) {
  const withImages = innovations.filter((i) => (i.images || [])[0]?.image)
  const shown = withImages.slice(0, 6)
  if (!shown.length) return null
  const shapes = ['wide', 'single', 'single', 'single', 'single', 'single']
  return (
    <section className="section section--surface work" aria-labelledby="work-title">
      <div className="wrap">
        <ul className="work__grid">
          <li className="work__head">
            <h2 id="work-title">Devices from the lab bench</h2>
            <p className="soft">Diagnostics, devices and digital tools developed at the centre for low-resource settings.</p>
            <SiteLink to="/innovations/" className="text-link">All {innovations.length} innovations</SiteLink>
          </li>
          {shown.map((inv, i) => {
            const img = inv.images[0]
            const shape = shapes[i % shapes.length]
            return (
              <li key={inv.id} className={`work__tile work__tile--${shape} work__tile--${i + 1}`}>
                <SiteLink to={`/innovations/#innovation-${inv.id}`} className="work__link">
                  <Img
                    src={img.image}
                    alt={img.image_alt || img.caption || ''}
                    figure
                    ratio="3x2"
                    sizes={shape === 'wide' ? '(min-width: 768px) 48vw, 100vw' : '(min-width: 768px) 24vw, 50vw'}
                  />
                  <span className="work__title">{inv.title}</span>
                </SiteLink>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}

/** From lab to manufacturing: the enterprise engagement text with its pictures and the facilities band. */
function Manufacturing({ home, equipment = [] }) {
  // The CMS facility-card images are clipart icons (docs/content-gaps.md), so each card shows the photograph of
  // the matching equipment row instead; a card with no matching photograph is set as a typographic tile.
  const panels = [1, 2, 3]
    .map((n) => ({ title: home[`facility_card_${n}_title`], link: home[`facility_card_${n}_link`] || '/facilities/' }))
    .filter((p) => p.title)
    .map((p) => ({ ...p, photo: facilityPhoto(p.title, equipment) }))
  if (!home.enterprises_text && !panels.length) return null
  return (
    <section className="section manufacture" aria-labelledby="manufacture-title">
      <div className="wrap grid12 manufacture__intro">
        <div className="manufacture__text">
          <h2 id="manufacture-title">From prototype to production</h2>
          {home.enterprises_text && <p>{home.enterprises_text}</p>}
          <div className="actions">
            <SiteLink to="/facilities/" className="btn btn--secondary">See the facilities</SiteLink>
            <SiteLink to="/enterprises/" className="text-link">Enterprise engagement</SiteLink>
          </div>
        </div>
        {home.enterprises_image_1 && (
          <figure className="manufacture__a">
            <Img src={home.enterprises_image_1} alt={home.enterprises_image_1_alt || ''} ratio="4x5" sizes="(min-width: 768px) 25vw, 60vw" />
          </figure>
        )}
        {home.enterprises_image_2 && (
          <figure className="manufacture__b">
            <Img src={home.enterprises_image_2} alt={home.enterprises_image_2_alt || ''} ratio="1x1" sizes="(min-width: 768px) 18vw, 40vw" />
          </figure>
        )}
      </div>
      {panels.length > 0 && (
        <div className="wrap">
          <h3 className="facility-list__title">Facilities at the centre</h3>
          <ul className="facility-list">
            {panels.map((p, i) => (
              <li key={p.title || i}>
                <SiteLink to={p.link} className={`facility-list__item${p.photo ? ' facility-list__item--photo' : ' facility-list__item--type'}`}>
                  {p.photo && <Img src={p.photo.image} alt={p.photo.image_alt || p.photo.name || ''} ratio="3x2" sizes="(min-width: 768px) 30vw, 40vw" />}
                  <span className="facility-list__name">{p.title}</span>
                  {!p.photo && <span className="facility-list__more">At the centre in IIT Kharagpur</span>}
                </SiteLink>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

const FACILITY_STOP = new Set(['crtdh', 'and', 'the', 'of', 'for', 'room', 'rooms', 'unit', 'units', 'facility', 'facilities'])
const facilityWords = (text) =>
  String(text || '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .map((w) => w.replace(/s$/, ''))
    .filter((w) => w.length > 2 && !FACILITY_STOP.has(w) && !FACILITY_STOP.has(`${w}s`))

/** The equipment row (with a photograph) that shares the most significant words with a facility card title. */
export function facilityPhoto(title, equipment) {
  const want = new Set(facilityWords(title))
  if (!want.size) return null
  let best = null
  let score = 0
  for (const e of equipment || []) {
    if (!e?.image) continue
    const s = facilityWords(e.name).filter((w) => want.has(w)).length
    if (s > score) {
      best = e
      score = s
    }
  }
  return best
}

/** In the community: the livelihood story with its two pictures, linking to Social Impact. */
function Community({ home }) {
  if (!home.women_text_1) return null
  return (
    <section className="section section--navy community on-navy" aria-labelledby="community-title">
      <div className="wrap grid12">
        {home.women_image_1 && (
          <figure className="community__a">
            <Img src={home.women_image_1} alt={home.women_image_1_alt || ''} ratio="3x2" sizes="(min-width: 768px) 42vw, 100vw" />
          </figure>
        )}
        <div className="community__text">
          <h2 id="community-title">Healthcare that reaches the village</h2>
          <p>{home.women_text_1}</p>
          <div className="actions">
            <SiteLink to="/social-impact/" className="btn btn--secondary">Read about our social impact</SiteLink>
          </div>
        </div>
        {home.women_image_2 && (
          <figure className="community__b">
            <Img src={home.women_image_2} alt={home.women_image_2_alt || ''} ratio="1x1" sizes="(min-width: 768px) 20vw, 50vw" />
          </figure>
        )}
      </div>
    </section>
  )
}

/** News: the latest items as a plain list pushed right, documents grouped below. */
function News({ items = [], documents = [], events = [], home }) {
  const videos = [
    { id: home.chintan_shivir_youtube_id, title: 'Chintan Shivir' },
    { id: home.viksit_bharat_youtube_id, title: 'Viksit Bharat Abhiyan' },
  ].filter((v) => v.id)
  if (!items.length && !documents.length && !videos.length) return null
  const photo = events.flatMap((e) => e.images || []).find((im) => im.image)
  return (
    <section className="section news" aria-labelledby="news-title">
      <div className="wrap">
        <h2 id="news-title" className="news__title">News from the centre</h2>
        <div className="grid12 news__body">
          {photo && (
            <figure className="news__photo">
              <Img src={photo.image} alt={photo.image_alt || photo.caption || ''} ratio="4x5" sizes="(min-width: 768px) 28vw, 60vw" />
            </figure>
          )}
          <div className="news__list">
            {items.length > 0 && (
              <ul className="rows" aria-label="Latest news">
                {items.map((n) => (
                  <li key={n.id}>
                    {n.link_url ? (
                      <SiteLink to={n.link_url} className="rows__link">
                        <span>{n.text}</span>
                        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8 3l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.8" /></svg>
                      </SiteLink>
                    ) : (
                      <span className="rows__text">{n.text}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {documents.length > 0 && (
              <>
                <h3 className="rows__group">Newsletters and brochures</h3>
                <ul className="rows">
                  {documents.map((d) => (
                    <li key={d.id}>
                      <PlainLink href={d.file} className="rows__link" download>
                        <span>{d.title}</span>
                        <span className="soft small">PDF</span>
                      </PlainLink>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <div className="actions">
              <SiteLink to="/media/" className="text-link">Photographs and press coverage</SiteLink>
            </div>
          </div>
        </div>
        {videos.length > 0 && (
          <div className="news__videos">
            {videos.map((v) => {
              const photo = eventPhotoFor(v.title, events)
              return (
                <VideoPoster
                  key={v.id}
                  url={`https://www.youtube.com/watch?v=${v.id}`}
                  title={v.title}
                  image={photo?.image}
                />
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}

/** Visit: where the centre is, how to reach it, and the MSME membership brochure. */
function Visit({ home, settings }) {
  const address = settings.address || home.location_address
  if (!address && !settings.email_primary) return null
  const maps = address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}` : null
  return (
    <section className="section section--surface visit" aria-labelledby="visit-title">
      <div className="wrap grid12">
        <div className="visit__text">
          <h2 id="visit-title">Visit the centre</h2>
          {home.location_description && <p className="lead">{home.location_description}.</p>}
          {address && <address>{address}</address>}
        </div>
        {home.office_image && (
          <figure className="visit__photo">
            <Img src={home.office_image} alt={home.office_image_alt || ''} ratio="1x1" sizes="200px" />
          </figure>
        )}
        <div className="visit__links">
          <p className="visit__q">Planning a visit or a partnership?</p>
          <ul>
            {settings.email_primary && (
              <li><a href={`mailto:${settings.email_primary}`}>{settings.email_primary}</a></li>
            )}
            {settings.phone_primary && (
              <li><a href={`tel:${settings.phone_primary.replace(/[^\d+]/g, '')}`}>{settings.phone_primary}</a></li>
            )}
            {maps && (
              <li><a href={maps} target="_blank" rel="noopener noreferrer">Directions in Google Maps</a></li>
            )}
          </ul>
          {home.membership_pdf && (
            <p className="visit__membership">
              <PlainLink href={home.membership_pdf} className="btn btn--primary" download>
                {home.membership_heading ? `${home.membership_heading} (PDF)` : 'MSME and startup membership (PDF)'}
              </PlainLink>
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
