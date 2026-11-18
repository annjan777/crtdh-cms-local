import { useRef, useState } from 'react'
import { Mail, MapPin, Phone } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchOne, postJSON } from '../api/client'
import PageHero from '../components/PageHero'
import { Spinner } from '../components/StateBlock'
import Reveal from '../components/Reveal'
import './Contact.css'

const EMPTY_FORM = { name: '', email: '', phone: '', message: '' }
const FIELDS = ['name', 'email', 'phone', 'message']
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Client-side checks mirror the backend's rules; the API stays the final authority.
function validateField(name, value) {
  const v = value.trim()
  switch (name) {
    case 'name':
      if (!v) return 'Please enter your name.'
      if (v.length > 255) return 'Please keep your name under 255 characters.'
      return ''
    case 'email':
      if (!v) return 'Please enter your email address.'
      if (!EMAIL_PATTERN.test(v)) return 'Please enter a valid email address, like name@example.com.'
      return ''
    case 'phone':
      if (v.length > 50) return 'Please keep the phone number under 50 characters.'
      return ''
    case 'message':
      if (!v) return 'Please write a message.'
      return ''
    default:
      return ''
  }
}

function validateAll(form) {
  const errors = {}
  for (const name of FIELDS) {
    const msg = validateField(name, form[name])
    if (msg) errors[name] = msg
  }
  return errors
}

// Turn a DRF field-error payload into plain sentences for known fields.
function errorsFromApi(err) {
  const data = err?.data
  if (!data || typeof data !== 'object') return {}
  const out = {}
  for (const name of FIELDS) {
    if (data[name]) {
      out[name] =
        name === 'email'
          ? 'Please enter a valid email address, like name@example.com.'
          : validateField(name, '') || 'Please check this field.'
    }
  }
  return out
}

function FieldError({ name, message }) {
  if (!message) return null
  return (
    <span className="field__error" id={`${name}-error`}>
      {message}
    </span>
  )
}

export default function Contact() {
  const { data: siteSettings, loading: settingsLoading } = useApi(
    () => fetchOne('/site-settings/'),
    [],
    null,
  )
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle') // idle | submitting | success | error
  const [errorMessage, setErrorMessage] = useState('')
  const dirty = useRef(new Set())

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    dirty.current.add(name)
    // Clear a field's error as soon as the user starts fixing it.
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
    if (status === 'success' || status === 'error') setStatus('idle')
  }

  const handleBlur = (e) => {
    const { name, value } = e.target
    // Don't nag about an empty field the user only tabbed past; submit catches those.
    if (!dirty.current.has(name)) return
    setErrors((prev) => ({ ...prev, [name]: validateField(name, value) }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const found = validateAll(form)
    setErrors(found)
    if (Object.keys(found).length) {
      setStatus('idle')
      const first = FIELDS.find((f) => found[f])
      document.getElementById(first)?.focus()
      return
    }

    setStatus('submitting')
    setErrorMessage('')
    try {
      await postJSON('/contact/', form)
      setStatus('success')
      setForm(EMPTY_FORM)
      setErrors({})
      dirty.current.clear()
    } catch (err) {
      const fieldErrors = errorsFromApi(err)
      if (Object.keys(fieldErrors).length) {
        setErrors(fieldErrors)
        setStatus('idle')
        const first = FIELDS.find((f) => fieldErrors[f])
        document.getElementById(first)?.focus()
        return
      }
      setStatus('error')
      setErrorMessage(
        err?.status === 0
          ? "We couldn't reach the server. Please check your connection and try again."
          : "Your message couldn't be sent right now. Please try again in a few minutes, or email us directly.",
      )
    }
  }

  const fieldProps = (name) => ({
    id: name,
    name,
    value: form[name],
    onChange: handleChange,
    onBlur: handleBlur,
    'aria-invalid': errors[name] ? 'true' : undefined,
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
  })

  const fieldClass = (name) => `field${errors[name] ? ' is-invalid' : ''}`

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
              <div className={fieldClass('name')}>
                <label htmlFor="name">
                  Name <span className="field__required" aria-hidden="true">*</span>
                </label>
                <input type="text" autoComplete="name" required {...fieldProps('name')} />
                <FieldError name="name" message={errors.name} />
              </div>
              <div className={fieldClass('email')}>
                <label htmlFor="email">
                  Email <span className="field__required" aria-hidden="true">*</span>
                </label>
                <input type="email" autoComplete="email" inputMode="email" required {...fieldProps('email')} />
                <FieldError name="email" message={errors.email} />
              </div>
              <div className={fieldClass('phone')}>
                <label htmlFor="phone">
                  Phone <span className="field__optional">(optional)</span>
                </label>
                <input type="tel" autoComplete="tel" {...fieldProps('phone')} />
                <FieldError name="phone" message={errors.phone} />
              </div>
              <div className={fieldClass('message')}>
                <label htmlFor="message">
                  Message <span className="field__required" aria-hidden="true">*</span>
                </label>
                <textarea rows={5} required {...fieldProps('message')} />
                <FieldError name="message" message={errors.message} />
              </div>

              <button
                className="btn btn--primary"
                type="submit"
                disabled={status === 'submitting'}
                aria-busy={status === 'submitting' ? 'true' : undefined}
              >
                {status === 'submitting' ? 'Sending…' : 'Send message'}
              </button>

              <div aria-live="polite">
                {status === 'success' && (
                  <p className="form-feedback form-feedback--success" role="status">
                    Thank you — your message has been sent. We’ll get back to you soon.
                  </p>
                )}
              </div>
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
