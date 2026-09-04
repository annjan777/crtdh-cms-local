import { Link } from 'react-router-dom'
import { ArrowRight, FlaskConical, HeartPulse, Users2, Activity, Map, Microscope, Users, Lightbulb, Building2, Calendar } from 'lucide-react'
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
    { label: 'Innovations developed', value: innovations?.length ?? 0, suffix: '+', icon: Lightbulb },
    { label: 'Enterprises incubated', value: enterprises?.length ?? 0, suffix: '+', icon: Building2 },
    { label: 'Researchers &amp; staff', value: team?.length ?? 0, suffix: '+', icon: Users },
    { label: 'Years sponsored by DSIR', value: 8, suffix: '+', icon: Calendar },
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
            <span className="eyebrow eyebrow--on-dark">
              {slides && slides[0]?.eyebrow ? slides[0].eyebrow : 'DSIR · Government of India'}
            </span>
            <h1>
              {slides && slides[0]?.heading ? slides[0].heading : 'Common Research &'}{' '}
              <span className="gradient-text">
                {slides && slides[0]?.highlight_heading ? slides[0].highlight_heading : 'Technology Development'}
              </span>{' '}
              {slides && slides[0]?.heading_end !== undefined ? slides[0].heading_end : 'Hub'}
            </h1>
            <p>
              {slides && slides[0]?.description
                ? slides[0].description
                : 'Building affordable healthcare technology for a billion people, at IIT Kharagpur.'}
            </p>
            <div className="hero__actions">
              <Link
                className="btn btn--accent"
                to={slides && slides[0]?.primary_button_link ? slides[0].primary_button_link : '/innovations'}
              >
                {slides && slides[0]?.primary_button_label ? slides[0].primary_button_label : 'Explore Innovations'}
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <Link
                className="btn btn--ghost"
                to={slides && slides[0]?.secondary_button_link ? slides[0].secondary_button_link : '/about'}
              >
                {slides && slides[0]?.secondary_button_label ? slides[0].secondary_button_label : 'About CRTDH'}
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
                <div className="stat-card__icon"><stat.icon size={28} /></div>
                <div>
                  <Counter value={stat.value} suffix={stat.suffix} className="stat-card__value" />
                  <span className="stat-card__label" dangerouslySetInnerHTML={{ __html: stat.label }} />
                </div>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="section">
        <div className="container home-split-1-3">
          <div className="home-split__left pr-6">
            <Reveal className="section-head">
              <span className="eyebrow">Who we are</span>
              <h2 className="section-title mt-4">Affordable healthcare for a billion people</h2>
              <p className="section-subtitle mt-4">
                CRTDH brings together research, engineering and enterprise to translate biomedical science into
                deployable, low-cost healthcare technology — from diagnostics and devices to sensors and digital
                health systems.
              </p>
              <br />
              <Link className="btn btn--primary" to="/about">
                Learn more <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </Reveal>
          </div>

          <div className="home-split__right">
            <Stagger className="grid grid--3 gap-4 h-100">
              <StaggerItem>
                <HighlightCard Icon={FlaskConical} title="Innovations" to="/innovations" text="Devices and diagnostics developed in-house, ready for translation." />
              </StaggerItem>
              <StaggerItem>
                <HighlightCard Icon={Building2} title="Enterprises" to="/enterprises" text="MSMEs and startups incubated at CRTDH with mentorship and support." />
              </StaggerItem>
              <StaggerItem>
                <HighlightCard Icon={Users2} title="Social Impact" to="/social-impact" text="Camps, clinics and outreach programmes bringing technology to communities." />
              </StaggerItem>
            </Stagger>
          </div>
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
              <section className="section objective-section">
                <div className="container home-split align-center">
                  <div className="home-split__left pr-6">
                    <Reveal className="section-head">
                      <span className="eyebrow">Objective</span>
                      <h2 className="section-title mt-4">Healthcare shouldn't depend on geography.</h2>
                      <p className="section-subtitle mt-4">
                        {home.objective_text}
                      </p>
                      <br />
                      <Link className="btn btn--primary" to="/about">
                        Read more <ArrowRight size={17} aria-hidden="true" />
                      </Link>
                    </Reveal>
                  </div>
                  <div className="home-split__right">
                    <Stagger className="grid grid--4 objective-impact-grid">
                      <StaggerItem className="impact-point">
                        <div className="impact-icon"><Activity size={24} /></div>
                        <h4>Accessible Healthcare</h4>
                      </StaggerItem>
                      <StaggerItem className="impact-point">
                        <div className="impact-icon"><Map size={24} /></div>
                        <h4>Rural Innovation</h4>
                      </StaggerItem>
                      <StaggerItem className="impact-point">
                        <div className="impact-icon"><Microscope size={24} /></div>
                        <h4>Medical Technology</h4>
                      </StaggerItem>
                      <StaggerItem className="impact-point">
                        <div className="impact-icon"><Users size={24} /></div>
                        <h4>Stronger Communities</h4>
                      </StaggerItem>
                    </Stagger>
                  </div>
                </div>
              </section>
            )}

            {home.enterprises_text && (
              <section className="section section--alt">
                <div className="container home-split align-center">
                  <div className="home-split__left">
                    <Reveal className="section-head">
                      <span className="eyebrow">Enterprises Engagement</span>
                      <h2 className="section-title">From innovation to impact</h2>
                      <p className="section-subtitle">
                        {home.enterprises_text}
                      </p>
                      <br />
                      <Link to="/enterprises" className="btn btn--primary">
                        Read more <ArrowRight size={17} aria-hidden="true" />
                      </Link>
                    </Reveal>
                  </div>
                  <div className="home-split__right">
                    {(home.enterprises_image_1 || home.enterprises_image_2) && (
                      <div className="grid grid--2 gap-4">
                        {home.enterprises_image_1 && (
                          <div className="image-card">
                            <img src={home.enterprises_image_1} alt="" className="rounded-lg shadow-sm" />
                            <p className="image-caption">Skill development and prototype manufacturing</p>
                          </div>
                        )}
                        {home.enterprises_image_2 && (
                          <div className="image-card">
                            <img src={home.enterprises_image_2} alt="" className="rounded-lg shadow-sm" />
                            <p className="image-caption">Pilot plant for medical device development</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}

            {home.women_text_1 && (
              <section className="section">
                <div className="container home-split align-center">
                  <div className="home-split__left">
                    <Reveal className="section-head">
                      <span className="eyebrow">Contribution to rural livelihood</span>
                      <h2 className="section-title">Technology reaching rural communities</h2>
                      <p className="section-subtitle">
                        {home.women_text_1}
                      </p>
                      <br />
                      <Link to="/social-impact" className="btn btn--primary">
                        Read more <ArrowRight size={17} aria-hidden="true" />
                      </Link>
                    </Reveal>
                  </div>
                  <div className="home-split__right">
                    {(home.women_image_1 || home.women_image_2) && (
                      <div className="grid grid--2 gap-4">
                        {home.women_image_1 && (
                          <div className="image-card">
                            <img src={home.women_image_1} alt="" className="rounded-lg shadow-sm" />
                            <p className="image-caption">Community healthcare and maternal support</p>
                          </div>
                        )}
                        {home.women_image_2 && (
                          <div className="image-card">
                            <img src={home.women_image_2} alt="" className="rounded-lg shadow-sm" />
                            <p className="image-caption">Awareness and outreach in rural communities</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}

            <section className="section section--alt section--dotted">
              <div className="container home-split-2-1">
                {/* Left Side: Facilities (2/3 width) */}
                <div className="home-split__left">
                  <div className="grid grid--2 gap-4">
                    <div>
                      <Reveal className="section-head">
                        <span className="eyebrow">Location &amp; Facility</span>
                        <h2 className="section-title mt-4">{home.location_address || 'Second Floor, Diamond Jubilee Building, IIT Kharagpur'}</h2>
                        <p className="section-subtitle mt-4">{home.location_description}</p>
                        <br />
                        <Link to="/facilities" className="btn btn--primary">
                          Explore Facilities <ArrowRight size={17} aria-hidden="true" />
                        </Link>
                      </Reveal>
                    </div>
                    <div>
                      <Stagger className="grid grid--3 facility-cards h-100">
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
                    </div>
                  </div>
                </div>

                {/* Right Side: Videos (1/3 width) */}
                {(home.chintan_shivir_youtube_id || home.viksit_bharat_youtube_id) && (
                  <div className="home-split__right">
                    <Reveal className="section-head">
                      <h2 className="section-title text-base font-bold">See CRTDH in action</h2>
                    </Reveal>
                    <div className="grid grid--2 home-videos mt-4">
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
                  </div>
                )}
              </div>
            </section>
          </>
        )
      )}

      {siteSettings?.map_embed_url && (
        <section className="section">
          <div className="container grid grid--3 gap-4 align-start">
            <div>
              <Reveal className="section-head">
                <span className="eyebrow">Find us</span>
                <h2 className="section-title">Visit CRTDH</h2>
                <p className="section-subtitle mt-4">
                  {home?.location_address || 'Diamond Jubilee Building, IIT Kharagpur'}
                </p>
                <br />
                <a href={siteSettings.map_embed_url} target="_blank" rel="noreferrer" className="btn btn--primary">
                  Get Directions <ArrowRight size={17} aria-hidden="true" />
                </a>
              </Reveal>
            </div>
            <div>
              <Reveal delay={0.1} className="map-embed card shadow-sm" style={{ height: '100%', minHeight: '250px' }}>
                <iframe
                  src={siteSettings.map_embed_url}
                  title="CRTDH location map"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                  style={{ width: '100%', height: '100%', border: 0 }}
                />
              </Reveal>
            </div>
            <div>
              <Reveal delay={0.2} className="quote-block shadow-sm">
                <h3>"Innovation for Inclusive Healthcare"</h3>
              </Reveal>
            </div>
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
          <Icon size={24} aria-hidden="true" />
        </span>
        <h3>{title}</h3>
        <p>{text}</p>
        <span className="highlight-card__cta">
          Explore <ArrowRight size={15} aria-hidden="true" />
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
