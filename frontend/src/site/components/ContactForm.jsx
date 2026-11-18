import { useEffect, useRef, useState } from 'react'

/* global __CONTACT_API_URL__, __TURNSTILE_SITE_KEY__ */
const API = typeof __CONTACT_API_URL__ !== 'undefined' ? __CONTACT_API_URL__ : ''
const SITE_KEY = typeof __TURNSTILE_SITE_KEY__ !== 'undefined' ? __TURNSTILE_SITE_KEY__ : ''
const FIELDS = ['name', 'email', 'phone', 'message']
const EMPTY = { name: '', email: '', phone: '', message: '', website: '' }
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Mirrors the relay's rules (backend apps/contact/serializers.py); the server stays the authority.
export function validateField(name, raw) {
  const v = String(raw || '').trim()
  switch (name) {
    case 'name':
      if (!v) return 'Enter your name.'
      if (v.length < 2) return 'Enter at least 2 characters for your name.'
      if (v.length > 120) return 'Keep your name under 120 characters.'
      return ''
    case 'email':
      if (!v) return 'Enter your email address so we can reply.'
      if (!EMAIL.test(v) || v.length > 254) return 'Enter an email address like name@example.com.'
      return ''
    case 'phone':
      if (v && !/^[0-9+()\-\s]{6,25}$/.test(v)) return 'Enter a phone number with digits, spaces, + or -, or leave it empty.'
      return ''
    case 'message':
      if (!v) return 'Write your message.'
      if (v.length < 10) return 'Write at least 10 characters so we know how to help.'
      if (v.length > 4000) return 'Keep the message under 4,000 characters.'
      return ''
    default:
      return ''
  }
}

export function mailtoHref(to, form) {
  const body = [
    form.message,
    '',
    `— ${form.name || ''}`,
    form.email ? `Email: ${form.email}` : '',
    form.phone ? `Phone: ${form.phone}` : '',
  ]
    .filter((l, i) => l !== '' || i === 1)
    .join('\n')
  return `mailto:${to}?subject=${encodeURIComponent('Enquiry from the CRTDH website')}&body=${encodeURIComponent(body)}`
}

function loadTurnstile() {
  if (!SITE_KEY || typeof window === 'undefined') return Promise.resolve(null)
  if (window.turnstile) return Promise.resolve(window.turnstile)
  return new Promise((resolve) => {
    const s = document.createElement('script')
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    s.async = true
    s.onload = () => resolve(window.turnstile || null)
    s.onerror = () => resolve(null)
    document.head.appendChild(s)
  })
}

/**
 * Contact form. States: idle → sending → sent; field errors on blur; Turnstile failure;
 * rate limited (429); relay unreachable → a prepared email (mailto) instead.
 * The submit button is never disabled; it reports what is missing.
 */
export default function ContactForm({ email, notice }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState('idle') // idle | sending | sent | turnstile | limited | offline | failed
  const [serverMessage, setServerMessage] = useState('')
  const touched = useRef(new Set())
  const tsBox = useRef(null)
  const tsWidget = useRef(null)
  const tsToken = useRef('')
  const feedback = useRef(null)

  useEffect(() => {
    if (['sent', 'turnstile', 'limited', 'offline', 'failed'].includes(status)) feedback.current?.focus()
  }, [status])

  async function ensureTurnstile() {
    if (!SITE_KEY || tsWidget.current !== null || !tsBox.current) return
    tsWidget.current = 'loading'
    const ts = await loadTurnstile()
    if (!ts) {
      tsWidget.current = null
      return
    }
    tsWidget.current = ts.render(tsBox.current, {
      sitekey: SITE_KEY,
      callback: (t) => (tsToken.current = t),
      'expired-callback': () => (tsToken.current = ''),
      'error-callback': () => (tsToken.current = ''),
    })
  }

  const onChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
    if (errors[name]) setErrors((x) => ({ ...x, [name]: '' }))
    if (touched.current.has(name) && errors[name] === undefined) {
      /* first blur not reached yet: stay quiet while typing */
    }
    if (status !== 'idle' && status !== 'sending') setStatus('idle')
  }

  const onBlur = (e) => {
    const { name, value } = e.target
    // An empty field the visitor only tabbed through is checked on send, not on blur.
    if (!value && !touched.current.has(name)) return
    touched.current.add(name)
    setErrors((x) => ({ ...x, [name]: validateField(name, value) }))
  }

  const onFocus = (e) => {
    ensureTurnstile()
    const { name } = e.target
    if (errors[name]) setErrors((x) => ({ ...x, [name]: '' }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    const found = {}
    for (const f of FIELDS) {
      const m = validateField(f, form[f])
      if (m) found[f] = m
    }
    FIELDS.forEach((f) => touched.current.add(f))
    setErrors(found)
    const first = FIELDS.find((f) => found[f])
    if (first) {
      document.getElementById(`contact-${first}`)?.focus()
      return
    }
    if (!API) {
      setStatus('offline')
      return
    }
    setStatus('sending')
    setServerMessage('')
    let res
    try {
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), 15000)
      res = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ ...form, turnstile_token: tsToken.current }),
        signal: ctrl.signal,
        credentials: 'omit',
      })
      clearTimeout(timer)
    } catch {
      setStatus('offline')
      return
    }
    let body = null
    try {
      body = await res.json()
    } catch {
      body = null
    }
    if (res.ok) {
      setServerMessage(body?.message || '')
      setStatus('sent')
      setForm(EMPTY)
      setErrors({})
      touched.current.clear()
      if (tsWidget.current && window.turnstile) window.turnstile.reset(tsWidget.current)
      return
    }
    if (res.status === 429) return setStatus('limited')
    const field = body?.field || (body && FIELDS.find((f) => body[f]))
    if (field === 'turnstile_token' || /turnstile|bot/i.test(body?.message || '')) {
      if (tsWidget.current && window.turnstile) window.turnstile.reset(tsWidget.current)
      return setStatus('turnstile')
    }
    if (res.status === 400 && field && FIELDS.includes(field)) {
      setErrors({ [field]: validateField(field, form[field]) || body?.fix || 'Check this field and send again.' })
      setStatus('idle')
      document.getElementById(`contact-${field}`)?.focus()
      return
    }
    if (res.status >= 500 || res.status === 0 || res.status === 404 || res.status === 502 || res.status === 503) {
      return setStatus('offline')
    }
    setStatus('failed')
  }

  const fieldProps = (name) => ({
    id: `contact-${name}`,
    name,
    value: form[name],
    onChange,
    onBlur,
    onFocus,
    'aria-invalid': errors[name] ? 'true' : undefined,
    'aria-describedby': [errors[name] ? `contact-${name}-error` : '', name === 'message' ? 'contact-message-hint' : ''].filter(Boolean).join(' ') || undefined,
  })
  const Err = ({ name }) =>
    errors[name] ? (
      <p className="field__error" id={`contact-${name}-error`}>
        {errors[name]}
      </p>
    ) : null

  return (
    <form className="form" onSubmit={onSubmit} noValidate aria-labelledby="contact-form-title" data-testid="contact-form">
      <h2 id="contact-form-title">Send a message</h2>
      <p className="soft mt-2">All fields except phone are needed.</p>

      <div className={`field${errors.name ? ' is-invalid' : ''}`}>
        <label htmlFor="contact-name">Your name</label>
        <input type="text" autoComplete="name" required maxLength={120} {...fieldProps('name')} />
        <Err name="name" />
      </div>
      <div className={`field${errors.email ? ' is-invalid' : ''}`}>
        <label htmlFor="contact-email">Email</label>
        <input type="email" autoComplete="email" inputMode="email" required maxLength={254} {...fieldProps('email')} />
        <Err name="email" />
      </div>
      <div className={`field${errors.phone ? ' is-invalid' : ''}`}>
        <label htmlFor="contact-phone">
          Phone <span className="soft">(optional)</span>
        </label>
        <input type="tel" autoComplete="tel" inputMode="tel" maxLength={25} {...fieldProps('phone')} />
        <Err name="phone" />
      </div>
      <div className={`field${errors.message ? ' is-invalid' : ''}`}>
        <label htmlFor="contact-message">Message</label>
        <textarea rows={6} required maxLength={4000} {...fieldProps('message')} />
        <p className="field__hint soft small" id="contact-message-hint">
          Tell us what you are working on and how the centre can help.
        </p>
        <Err name="message" />
      </div>
      {/* Honeypot for bots; hidden from people and assistive technology. */}
      <div className="hp" aria-hidden="true">
        <label htmlFor="contact-website">Website</label>
        <input id="contact-website" name="website" tabIndex={-1} autoComplete="off" value={form.website} onChange={onChange} />
      </div>
      {SITE_KEY && <div ref={tsBox} className="turnstile" />}

      {notice}
      <div className="form__send">
        <button className="btn btn--primary" type="submit" aria-busy={status === 'sending' ? 'true' : undefined}>
          {status === 'sending' ? 'Sending…' : 'Send message'}
        </button>
      </div>

      <div className="form__feedback" aria-live="polite">
        {status === 'sent' && (
          <div className="notice notice--ok" role="status" tabIndex={-1} ref={feedback}>
            <p><strong>Message sent.</strong> {serverMessage || 'We have your message and will reply by email.'}</p>
          </div>
        )}
        {status === 'turnstile' && (
          <div className="notice notice--error" role="alert" tabIndex={-1} ref={feedback}>
            <p>The anti-spam check did not complete, so nothing was sent. Complete the check above and send again; your text is still here.</p>
          </div>
        )}
        {status === 'limited' && (
          <div className="notice notice--error" role="alert" tabIndex={-1} ref={feedback}>
            <p>Too many messages came from this connection just now, so this one was not sent. Wait a minute and send again; your text is still here.</p>
          </div>
        )}
        {(status === 'offline' || status === 'failed') && (
          <div className="notice notice--error" role="alert" tabIndex={-1} ref={feedback} data-testid="contact-fallback">
            <p>
              {status === 'offline'
                ? 'The message service is not reachable right now, so nothing was sent.'
                : 'The message could not be sent.'}{' '}
              {email ? 'Send it from your email app instead; your text is copied into the email.' : 'Please try again later.'}
            </p>
            {email && (
              <p className="mt-4">
                <a className="btn btn--secondary" href={mailtoHref(email, form)}>
                  Email {email}
                </a>
              </p>
            )}
          </div>
        )}
      </div>

    </form>
  )
}
