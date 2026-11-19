import { PageDataProvider } from '../api/data.jsx'
import { mapEmbedUrl } from '../util.js'
import { Mail, MapPin, Phone } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchOne } from '../api/client'
import { usePageData } from '../api/data.jsx'
import ContactForm from '../components/ContactForm.jsx'
import { FullNotice, ShortNotice } from '../components/PrivacyNotice.jsx'
import PageHero from '../components/PageHero'
import { Spinner } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Contact.css'

function ContactView() {
  const { data: siteSettings, loading: settingsLoading } = useApi(
    () => fetchOne('/site-settings/'),
    [],
    null,
  )
  const privacy = usePageData()?.extra?.privacy

  return (
    <div>
      <PageHero
        eyebrow="Contact"
        title="Get in touch"
        description="Questions about our research, facilities, or partnering with CRTDH? Send us a message."
      />

      <section data-block="contact.details" className="section">
        <div className="container contact-layout">
          <Reveal direction="left" className="card contact-form-wrap">
            <ContactForm
              email={siteSettings?.email_primary}
              phone={siteSettings?.phone_primary}
              notice={<ShortNotice privacy={privacy} />}
            />
          </Reveal>

          <Reveal direction="right" delay={0.1} className="contact-details">
            <h2>Our office</h2>
            {settingsLoading ? (
              <Spinner />
            ) : siteSettings ? (
              <ul className="contact-details__list">
                {siteSettings.address && (
                  <li>
                    <MapPin size={18} aria-hidden="true" />
                    <div>
                      <strong>Address</strong>
                      <span>{siteSettings.address}</span>
                    </div>
                  </li>
                )}
                {(siteSettings.phone_primary || siteSettings.phone_secondary) && (
                  <li>
                    <Phone size={18} aria-hidden="true" />
                    <div>
                      <strong>Phone</strong>
                      <span>
                        {[siteSettings.phone_primary, siteSettings.phone_secondary].filter(Boolean).join(', ')}
                      </span>
                    </div>
                  </li>
                )}
                {(siteSettings.email_primary || siteSettings.email_secondary) && (
                  <li>
                    <Mail size={18} aria-hidden="true" />
                    <div>
                      <strong>Email</strong>
                      <span>
                        {[siteSettings.email_primary, siteSettings.email_secondary].filter(Boolean).join(', ')}
                      </span>
                    </div>
                  </li>
                )}
              </ul>
            ) : (
              <p className="contact-details__empty">Contact details are being updated. Please use the form.</p>
            )}

            {mapEmbedUrl(siteSettings?.map_embed_url) && (
              <div className="map-embed card contact-map">
                <iframe
                  src={mapEmbedUrl(siteSettings.map_embed_url)}
                  title="CRTDH location map"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            )}
          </Reveal>
        </div>
      </section>
      <FullNotice privacy={privacy} />
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function Contact({ data }) {
  return (
    <PageDataProvider data={data}>
      <ContactView />
    </PageDataProvider>
  )
}
