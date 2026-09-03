import { useState } from 'react'
import { Mail, MapPin, Phone } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchOne, postJSON } from '../api/client'
import PageHero from '../components/PageHero'
import { Spinner } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Contact.css'

const EMPTY_FORM = { name: '', email: '', phone: '', message: '' }

export default function Contact() {
  const { data: siteSettings, loading: settingsLoading } = useApi(
    () => fetchOne('/site-settings/'),
    [],
    null,
  )
  const [form, setForm] = useState(EMPTY_FORM)
  const [status, setStatus] = useState('idle') // idle | submitting | success | error
  const [errorMessage, setErrorMessage] = useState('')

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('submitting')
    setErrorMessage('')
    try {
      await postJSON('/contact/', form)
      setStatus('success')
      setForm(EMPTY_FORM)
    } catch (err) {
      setStatus('error')
      setErrorMessage(err?.message || 'Something went wrong. Please try again.')
    }
  }

  return (
    <div>
      <PageHero
        eyebrow="Contact"
        title="Get in touch"
        description="Questions about our research, facilities, or partnering with CRTDH? Send us a message."
      />

      <section className="section">
        <div className="container contact-layout">
          <Reveal direction="left" className="card contact-form-wrap">
            <h2>Send a message</h2>
            <form onSubmit={handleSubmit} noValidate>
              <div className="field">
                <label htmlFor="name">Name</label>
                <input id="name" name="name" type="text" required value={form.name} onChange={handleChange} />
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input id="email" name="email" type="email" required value={form.email} onChange={handleChange} />
              </div>
              <div className="field">
                <label htmlFor="phone">Phone</label>
                <input id="phone" name="phone" type="tel" value={form.phone} onChange={handleChange} />
              </div>
              <div className="field">
                <label htmlFor="message">Message</label>
                <textarea
                  id="message"
                  name="message"
                  rows={5}
                  required
                  value={form.message}
                  onChange={handleChange}
                />
              </div>

              <button className="btn btn--primary" type="submit" disabled={status === 'submitting'}>
                {status === 'submitting' ? 'Sending…' : 'Send message'}
              </button>

              {status === 'success' && (
                <p className="form-feedback form-feedback--success" role="status">
                  Thanks — your message has been sent. We'll get back to you soon.
                </p>
              )}
              {status === 'error' && (
                <p className="form-feedback form-feedback--error" role="alert">
                  {errorMessage}
                </p>
              )}
            </form>
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

            {siteSettings?.map_embed_url && (
              <div className="map-embed card contact-map">
                <iframe
                  src={siteSettings.map_embed_url}
                  title="CRTDH location map"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            )}
          </Reveal>
        </div>
      </section>
    </div>
  )
}
