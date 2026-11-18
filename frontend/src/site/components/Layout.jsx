import { useEffect, useRef } from 'react'
import SiteLink from '../link.jsx'
import { toRoute, formatDate } from '../util.js'

// Grouped navigation (PLAN WS2.2): About · Our work · Impact · News · Contact.
// Labels and order come from the CMS nav items; the group is chosen by route.
const GROUPS = [
  { id: 'about', label: 'About', routes: ['/about', '/team'] },
  { id: 'work', label: 'Our work', routes: ['/innovations', '/facilities', '/services', '/product', '/enterprises'] },
  { id: 'impact', label: 'Impact', routes: ['/social-impact', '/covid-19'] },
  { id: 'news', label: 'News', routes: ['/media'] },
]
const CONTACT = '/contact'

export function groupNav(navItems) {
  const items = (navItems || []).map((n) => ({ ...n, route: toRoute(n.url) })).filter((n) => n.route !== '/')
  const used = new Set()
  const groups = GROUPS.map((g) => {
    const members = items.filter((n) => g.routes.includes(n.route))
    members.forEach((m) => used.add(m))
    return { ...g, items: members }
  }).filter((g) => g.items.length)
  const contact = items.find((n) => n.route === CONTACT)
  if (contact) used.add(contact)
  // Anything the CMS adds that we do not know yet still appears, under About.
  const rest = items.filter((n) => !used.has(n))
  if (rest.length) {
    const about = groups.find((g) => g.id === 'about')
    if (about) about.items.push(...rest)
    else groups.unshift({ id: 'about', label: 'About', routes: [], items: rest })
  }
  return { groups, contact }
}

const isActive = (current, route) => (route === '/' ? current === '/' : current === route || current.startsWith(`${route}/`))

/** Site chrome: skip link, header with grouped nav, main landmark, footer. Props only. */
export default function Layout({ data, currentPath = '/', children }) {
  const settings = data?.singletons?.['site-settings'] || {}
  const navItems = data?.collections?.['nav-items'] || []
  const { groups, contact } = groupNav(navItems)
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <Header settings={settings} groups={groups} contact={contact} currentPath={currentPath} />
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <Footer settings={settings} groups={groups} contact={contact} publishedAt={data?.meta?.published_at} />
    </>
  )
}

function useCloseOnOutside(ref) {
  useEffect(() => {
    function onDoc(e) {
      ref.current?.querySelectorAll('details[open]').forEach((d) => {
        if (!d.contains(e.target)) d.removeAttribute('open')
      })
    }
    function onKey(e) {
      if (e.key !== 'Escape') return
      const open = ref.current?.querySelector('details[open]')
      if (open) {
        open.removeAttribute('open')
        open.querySelector('summary')?.focus()
      }
    }
    document.addEventListener('click', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('click', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [ref])
}

function Header({ settings, groups, contact, currentPath }) {
  const ref = useRef(null)
  useCloseOnOutside(ref)
  return (
    <header className="site-header" ref={ref}>
      <div className="wrap site-header__bar">
        <SiteLink to="/" className="wordmark" aria-label="CRTDH, IIT Kharagpur — home">
          {settings.site_logo && <img src={settings.site_logo} alt="" width="40" height="40" className="wordmark__logo" />}
          <span className="wordmark__text">
            <span className="wordmark__name">CRTDH</span>
            <span className="wordmark__sub">IIT Kharagpur</span>
          </span>
        </SiteLink>

        <nav className="nav" aria-label="Main">
          <ul className="nav__list">
            {groups.map((g) =>
              g.items.length === 1 ? (
                <li key={g.id}>
                  <SiteLink
                    to={g.items[0].route}
                    className="nav__link"
                    aria-current={isActive(currentPath, g.items[0].route) ? 'page' : undefined}
                  >
                    {g.label}
                  </SiteLink>
                </li>
              ) : (
                <li key={`${g.id}-${currentPath}`}>
                  <details className="nav__group">
                    <summary
                      className={`nav__link${g.items.some((i) => isActive(currentPath, i.route)) ? ' is-current' : ''}`}
                    >
                      {g.label}
                      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.8" /></svg>
                    </summary>
                    <ul className="nav__menu">
                      {g.items.map((i) => (
                        <li key={i.id ?? i.route}>
                          <SiteLink to={i.route} aria-current={isActive(currentPath, i.route) ? 'page' : undefined}>
                            {i.label}
                          </SiteLink>
                        </li>
                      ))}
                    </ul>
                  </details>
                </li>
              ),
            )}
          </ul>
        </nav>

        {contact && (
          <SiteLink to={contact.route} className="btn btn--primary site-header__action">
            {contact.label}
          </SiteLink>
        )}

        <details className="mnav" key={`m-${currentPath}`}>
          <summary className="mnav__toggle">
            <span className="mnav__open">Menu</span>
            <span className="mnav__close">Close</span>
          </summary>
          <nav className="mnav__panel" aria-label="Main (mobile)">
            {groups.map((g) => (
              <div className="mnav__group" key={g.id}>
                <p className="mnav__label">{g.label}</p>
                <ul>
                  {g.items.map((i) => (
                    <li key={i.id ?? i.route}>
                      <SiteLink to={i.route} aria-current={isActive(currentPath, i.route) ? 'page' : undefined}>
                        {i.label}
                      </SiteLink>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {contact && (
              <SiteLink to={contact.route} className="btn btn--primary mnav__action">
                {contact.label}
              </SiteLink>
            )}
          </nav>
        </details>
      </div>
    </header>
  )
}

function Footer({ settings, groups, contact, publishedAt }) {
  const year = (publishedAt ? new Date(publishedAt) : new Date()).getUTCFullYear()
  const phones = [settings.phone_primary, settings.phone_secondary].filter(Boolean)
  const emails = [settings.email_primary, settings.email_secondary].filter(Boolean)
  const social = [
    ['Facebook', settings.facebook_url],
    ['LinkedIn', settings.linkedin_url],
    ['Instagram', settings.instagram_url],
    ['X (Twitter)', settings.twitter_url],
  ].filter(([, href]) => href)
  return (
    <footer className="site-footer on-navy">
      <div className="wrap">
        <p className="site-footer__name">
          Common Research and Technology Development Hub on Affordable Healthcare
        </p>
        <div className="site-footer__grid">
          <div className="site-footer__contact">
            <h2 className="site-footer__h">Visit</h2>
            {settings.address && <address>{settings.address}</address>}
            {phones.length > 0 && (
              <p>
                {phones.map((p, i) => (
                  <span key={p}>
                    {i > 0 && ', '}
                    <a href={`tel:${p.replace(/[^\d+]/g, '')}`}>{p}</a>
                  </span>
                ))}
              </p>
            )}
            {emails.length > 0 && (
              <p>
                {emails.map((e, i) => (
                  <span key={e}>
                    {i > 0 && <br />}
                    <a href={`mailto:${e}`}>{e}</a>
                  </span>
                ))}
              </p>
            )}
            {social.length > 0 && (
              <ul className="site-footer__social">
                {social.map(([label, href]) => (
                  <li key={label}>
                    <a href={href} target="_blank" rel="noopener noreferrer">{label}</a>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <nav className="site-footer__nav" aria-label="Footer">
            {groups.map((g) => (
              <div key={g.id}>
                <h2 className="site-footer__h">{g.label}</h2>
                <ul>
                  {g.items.map((i) => (
                    <li key={i.id ?? i.route}>
                      <SiteLink to={i.route}>{i.label}</SiteLink>
                    </li>
                  ))}
                  {g.id === 'news' && contact && (
                    <li>
                      <SiteLink to={contact.route}>{contact.label}</SiteLink>
                    </li>
                  )}
                </ul>
              </div>
            ))}
          </nav>
        </div>
        <div className="site-footer__base">
          <div className="site-footer__logos">
            {settings.logo_left && <img src={settings.logo_left} alt="Indian Institute of Technology Kharagpur" height="56" loading="lazy" />}
            {settings.logo_right && <img src={settings.logo_right} alt="Department of Scientific and Industrial Research, Government of India" height="56" loading="lazy" />}
          </div>
          <p className="small">
            A DSIR-sponsored centre at IIT Kharagpur. © {year} CRTDH, IIT Kharagpur.{' '}
            <SiteLink to="/contact#privacy">How we use contact messages</SiteLink>.
            {publishedAt && <> Last updated {formatDate(publishedAt)}.</>}
          </p>
        </div>
      </div>
    </footer>
  )
}
