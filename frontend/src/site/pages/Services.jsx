import PageShell from '../components/PageShell.jsx'
import { PageBanner } from '../components/Blocks.jsx'
import SiteLink, { PlainLink } from '../link.jsx'
import { Img } from '../media.jsx'

/** Services (listing): what the centre offers MSMEs and startups, and how to start. */
export default function Services({ data }) {
  const services = data.collections?.services || []
  const home = data.singletons?.['home-page'] || {}
  return (
    <PageShell data={data} className="services">
      <PageBanner
        title="Services"
        intro="Support for healthcare MSMEs, startups and innovators, from research and prototyping to regulation, training and market access."
      >
        <div className="actions">
          <SiteLink to="/contact/" className="btn btn--primary">Ask about a service</SiteLink>
          {home.membership_pdf && (
            <PlainLink href={home.membership_pdf} className="text-link" download>
              {home.membership_heading ? `${home.membership_heading} (PDF)` : 'Membership brochure (PDF)'}
            </PlainLink>
          )}
        </div>
      </PageBanner>
      {services.length > 0 && (
        <section className="section" aria-labelledby="services-list">
          <div className="wrap">
            <h2 id="services-list" className="visually-hidden">What we offer</h2>
            <ul className="services__list">
              {services.map((s) => (
                <li key={s.id} className="services__item">
                  {s.image && <Img src={s.image} alt={s.image_alt || ''} ratio="3x2" sizes="(min-width: 768px) 30vw, 100vw" />}
                  <h3>{(s.title || '').replace('R & D', 'R&D')}</h3>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </PageShell>
  )
}
