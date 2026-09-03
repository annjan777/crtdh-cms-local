import { Link } from 'react-router-dom'
import { ArrowRight, FlaskConical, HeartPulse, Users2 } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchList, fetchOne } from '../api/client'
import Carousel from '../components/Carousel'
import VideoBlock from '../components/VideoBlock'
import { Spinner } from '../components/StateBlock'
import Reveal, { Stagger, StaggerItem } from '../components/Reveal'
import TiltCard from '../components/TiltCard'
import Counter from '../components/Counter'
import './Home.css'

const MEMBERSHIP_TIERS = [
  { label: 'Platinum', bg: '#e5e4e2' },
  { label: 'Gold', bg: '#ffd700' },
  { label: 'Silver', bg: '#c0c0c0' },
]

export default function Home() {
  const { data: slides, loading: slidesLoading } = useApi(() => fetchList('/hero-slides/'), [], [])
  const { data: newsItems, loading: newsLoading } = useApi(() => fetchList('/news-items/'), [], [])
  const { data: home, loading: homeLoading } = useApi(() => fetchOne('/home-page/'), [], null)
  const { data: siteSettings } = useApi(() => fetchOne('/site-settings/'), [], null)
  const { data: team } = useApi(() => fetchList('/team-members/'), [], [])
  const { data: innovations } = useApi(() => fetchList('/innovations/'), [], [])
  const { data: enterprises } = useApi(() => fetchList('/enterprises/'), [], [])

  const stats = [
    { label: 'Innovations developed', value: innovations?.length ?? 0, suffix: '+' },
    { label: 'Enterprises incubated', value: enterprises?.length ?? 0, suffix: '+' },
    { label: 'Researchers &amp; staff', value: team?.length ?? 0, suffix: '+' },
    { label: 'Years sponsored by DSIR', value: 8, suffix: '+' },
  ]

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero__grid" aria-hidden="true" />

        {slidesLoading ? (
          <div className="hero__fallback">
            <Spinner label="Loading…" />
          </div>
        ) : slides && slides.length > 0 ? (
          <Carousel
            items={slides}
            ariaLabel="Hero image carousel"
            renderItem={(slide) => (
              <div className="hero__slide">
                <img src={slide.image} alt="" />
              </div>
            )}
          />
        ) : (
          <div className="hero__fallback hero__fallback--static" />
        )}

        <div className="hero__caption container">
          <div className="hero__caption-inner">
            <span className="eyebrow eyebrow--on-dark">DSIR · Government of India</span>
            <h1>
              Common Research &amp; <span className="gradient-text">Technology Development</span> Hub
            </h1>
            <p>Building affordable healthcare technology for a billion people, at IIT Kharagpur.</p>
            <div className="hero__actions">
              <Link className="btn btn--accent" to="/innovations">
                Explore Innovations
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <Link className="btn btn--ghost" to="/about">
                About CRTDH
              </Link>
            </div>
          </div>
        </div>

        <div className="hero__scroll-cue" aria-hidden="true">
          <span />
        </div>
      </section>

      <NewsMarquee items={newsItems} loading={newsLoading} />

      <section className="section stats-strip">
        <div className="container">
          <Stagger className="stats-strip__grid">
            {stats.map((stat) => (
              <StaggerItem as="div" className="stat-card" key={stat.label}>
                <Counter value={stat.value} suffix={stat.suffix} className="stat-card__value" />
                <span className="stat-card__label" dangerouslySetInnerHTML={{ __html: stat.label }} />
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-7)' }}>
            <span className="eyebrow">Who we are</span>
            <h2 className="section-title">Affordable healthcare for a billion people</h2>
            <p className="section-subtitle">
              CRTDH brings together research, engineering and enterprise to translate biomedical science into
              deployable, low-cost healthcare technology — from diagnostics and devices to sensors and digital
              health systems.
            </p>
          </Reveal>

          <Stagger className="grid grid--3">
            <StaggerItem>
              <HighlightCard Icon={FlaskConical} title="Innovations" to="/innovations" text="Devices and diagnostics developed in-house, ready for translation." />
            </StaggerItem>
            <StaggerItem>
              <HighlightCard Icon={Users2} title="Enterprises" to="/enterprises" text="MSMEs and startups CRTDH incubates and mentors toward market." />
            </StaggerItem>
            <StaggerItem>
              <HighlightCard Icon={HeartPulse} title="Social Impact" to="/social-impact" text="Camps, clinics and outreach bringing technology to rural communities." />
            </StaggerItem>
          </Stagger>
        </div>
      </section>

      {homeLoading ? (
        <div className="section">
          <div className="container">
            <Spinner />
          </div>
        </div>
      ) : (
        home && (
          <>
            {(home.membership_pdf || home.membership_heading) && (
              <section className="section section--alt membership-section">
                <div className="container text-center">
                  <h2 className="section-title">{home.membership_heading || 'Annual Membership for MSME / Startup'}</h2>
                  <div className="membership-tiers">
                    {MEMBERSHIP_TIERS.map((tier) =>
                      home.membership_pdf ? (
                        <a
                          key={tier.label}
                          className="membership-tier"
                          style={{ background: tier.bg }}
                          href={home.membership_pdf}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {tier.label}
                        </a>
                      ) : (
                        <span key={tier.label} className="membership-tier" style={{ background: tier.bg }}>
                          {tier.label}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              </section>
            )}

            {home.objective_text && (
              <section className="section">
                <div className="container">
                  <Reveal className="section-head">
                    <span className="eyebrow">Objective</span>
                  </Reveal>
                  <Reveal delay={0.1} className="prose-block objective-text">
                    <p>
                      {home.objective_text}{' '}
                      <Link to="/about" className="text-link">
                        Read more..
                      </Link>
                    </p>
                  </Reveal>
                </div>
              </section>
            )}

            {home.enterprises_text && (
              <section className="section section--alt">
                <div className="container">
                  <Reveal className="section-head">
                    <span className="eyebrow">Enterprises Engagement</span>
                  </Reveal>
                  <Reveal delay={0.1} className="prose-block">
                    <p>
                      {home.enterprises_text}{' '}
                      <Link to="/enterprises" className="text-link">
                        Read more..
                      </Link>
                    </p>
                  </Reveal>
                  {(home.enterprises_image_1 || home.enterprises_image_2) && (
                    <div className="home-image-pair">
                      {home.enterprises_image_1 && <img src={home.enterprises_image_1} alt="" />}
                      {home.enterprises_image_2 && <img src={home.enterprises_image_2} alt="" />}
                    </div>
                  )}
                  {home.msme_map_image && (
                    <div className="msme-map">
                      <img src={home.msme_map_image} alt={home.msme_caption} />
                      {home.msme_caption && <h3>{home.msme_caption}</h3>}
                    </div>
                  )}
                </div>
              </section>
            )}

            {home.women_text_1 && (
              <section className="section">
                <div className="container">
                  <Reveal className="section-head">
                    <span className="eyebrow">Women Empowerment</span>
                    <h2 className="section-title">Contribution to rural livelihood</h2>
                  </Reveal>
                  <Reveal delay={0.1} className="prose-block">
                    <p>{home.women_text_1}</p>
                  </Reveal>
                  {(home.women_image_1 || home.women_image_2) && (
                    <div className="home-image-pair">
                      {home.women_image_1 && <img src={home.women_image_1} alt="" />}
                      {home.women_image_2 && <img src={home.women_image_2} alt="" />}
                    </div>
                  )}
                  {home.women_text_2 && (
                    <Reveal delay={0.1} className="prose-block">
                      <p>
                        {home.women_text_2}{' '}
                        <Link to="/social-impact" className="text-link">
                          Read more..
                        </Link>
                      </p>
                    </Reveal>
                  )}
                </div>
              </section>
            )}

            <section className="section section--alt section--dotted">
              <div className="container">
                <Reveal className="section-head text-center" style={{ margin: '0 auto var(--space-6)' }}>
                  <span className="eyebrow">Location &amp; Facility</span>
                  <h2 className="section-title">{home.location_address}</h2>
                  <p className="section-subtitle">{home.location_description}</p>
                </Reveal>

                <Stagger className="grid grid--3 facility-cards">
                  {[
                    { title: home.facility_card_1_title, image: home.facility_card_1_image, link: home.facility_card_1_link },
                    { title: home.facility_card_2_title, image: home.facility_card_2_image, link: home.facility_card_2_link },
                    { title: home.facility_card_3_title, image: home.facility_card_3_image, link: home.facility_card_3_link },
                  ]
                    .filter((c) => c.title || c.image)
                    .map((card) => {
                      const inner = (
                        <>
                          <div className="facility-card__img">
                            {card.image ? <img src={card.image} alt="" /> : <div className="facility-card__img--empty" />}
                          </div>
                          <h3>{card.title}</h3>
                        </>
                      )
                      return (
                        <StaggerItem as="div" className="facility-card" key={card.title}>
                          {card.link ? (
                            card.link.startsWith('/') ? (
                              <Link to={card.link}>{inner}</Link>
                            ) : (
                              <a href={card.link}>{inner}</a>
                            )
                          ) : (
                            inner
                          )}
                        </StaggerItem>
                      )
                    })}
                </Stagger>

                {(home.chintan_shivir_youtube_id || home.viksit_bharat_youtube_id) && (
                  <div className="grid grid--2 home-videos">
                    {home.chintan_shivir_youtube_id && (
                      <VideoBlock
                        block={{ title: 'Chintan Shivir', youtube_url: `https://www.youtube.com/watch?v=${home.chintan_shivir_youtube_id}` }}
                      />
                    )}
                    {home.viksit_bharat_youtube_id && (
                      <VideoBlock
                        block={{ title: 'Viksit Bharat Abhiyan', youtube_url: `https://www.youtube.com/watch?v=${home.viksit_bharat_youtube_id}` }}
                      />
                    )}
                  </div>
                )}

                {home.office_image && (
                  <div className="office-image">
                    <img src={home.office_image} alt="CRTDH office" />
                  </div>
                )}
              </div>
            </section>
          </>
        )
      )}

      {siteSettings?.map_embed_url && (
        <section className="section">
          <div className="container">
            <Reveal className="section-head">
              <span className="eyebrow">Find us</span>
              <h2 className="section-title">Visit CRTDH</h2>
            </Reveal>
            <Reveal delay={0.1} className="map-embed card">
              <iframe
                src={siteSettings.map_embed_url}
                title="CRTDH location map"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
            </Reveal>
          </div>
        </section>
      )}
    </div>
  )
}

function HighlightCard({ title, text, to, Icon }) {
  return (
    <TiltCard max={6} className="highlight-card-wrap">
      <Link to={to} className="card highlight-card">
        <span className="highlight-card__icon">
          <Icon size={22} aria-hidden="true" />
        </span>
        <h3>{title}</h3>
        <p>{text}</p>
        <span className="highlight-card__cta">
          Learn more <ArrowRight size={15} aria-hidden="true" />
        </span>
      </Link>
    </TiltCard>
  )
}

function NewsMarquee({ items, loading }) {
  if (loading) return null
  if (!items || items.length === 0) return null
  // Duplicate the list once so the CSS scroll animation can loop seamlessly.
  const looped = [...items, ...items]
  return (
    <div className="news-marquee">
      <span className="news-marquee__label">News &amp; Events</span>
      <div className="news-marquee__track-wrap">
        <div className="news-marquee__track">
          {looped.map((item, i) => (
            <span className="news-marquee__item" key={`${item.id ?? i}-${i}`}>
              {item.link_url ? (
                <a href={item.link_url} target="_blank" rel="noreferrer">
                  {item.text}
                </a>
              ) : (
                item.text
              )}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
