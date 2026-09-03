import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Mail, Menu, MapPin, Phone, X } from 'lucide-react'
import { FacebookIcon, InstagramIcon, LinkedinIcon, TwitterIcon } from './SocialIcons'
import { fetchList, fetchOne } from '../api/client'
import { SiteDataContext } from '../context/SiteDataContext'
import './Layout.css'

// Fallback nav used only while nav-items are loading/unreachable, so the
// header never renders completely empty (and the site stays navigable
// even if the backend is briefly down).
const FALLBACK_NAV = [
  { id: 'home', label: 'Home', url: '/' },
  { id: 'about', label: 'About', url: '/about' },
  { id: 'team', label: 'Team', url: '/team' },
  { id: 'innovations', label: 'Innovations', url: '/innovations' },
  { id: 'facilities', label: 'Facilities', url: '/facilities' },
  { id: 'services', label: 'Services', url: '/services' },
  { id: 'enterprises', label: 'Enterprises', url: '/enterprises' },
  { id: 'product', label: 'Product', url: '/product' },
  { id: 'social-impact', label: 'Social Impact', url: '/social-impact' },
  { id: 'covid-19', label: 'Covid-19', url: '/covid-19' },
  { id: 'media', label: 'Media', url: '/media' },
  { id: 'contact', label: 'Contact', url: '/contact' },
]

// The 12 real nav items are too many for one row at laptop widths. We keep
// the essentials always visible and tuck secondary destinations behind an
// animated "More" menu — this is the fix for the "messy multi-row navbar"
// complaint. Matching is by route slug so it stays correct even if the CMS
// relabels an item, and any unrecognised item safely falls into "More"
// rather than disappearing.
const PRIMARY_SLUGS = new Set(['/', 'about', 'team', 'innovations', 'facilities', 'services', 'enterprises'])
const CONTACT_SLUG = 'contact'

function slugOf(url) {
  const route = toRoute(url)
  return route === '/' ? '/' : route.replace(/^\//, '').replace(/\/$/, '')
}

export default function Layout() {
  const [navItems, setNavItems] = useState([])
  const [siteSettings, setSiteSettings] = useState(null)
  const [navLoading, setNavLoading] = useState(true)
  const [settingsLoading, setSettingsLoading] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    let cancelled = false
    fetchList('/nav-items/').then((items) => {
      if (!cancelled) {
        setNavItems(items)
        setNavLoading(false)
      }
    })
    fetchOne('/site-settings/').then((settings) => {
      if (!cancelled) {
        setSiteSettings(settings)
        setSettingsLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  const navToRender = navItems.length > 0 ? navItems : FALLBACK_NAV

  return (
    <SiteDataContext.Provider value={{ navItems: navToRender, siteSettings, navLoading, settingsLoading }}>
      <div className="app-shell">
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <SiteHeader navItems={navToRender} siteSettings={siteSettings} menuOpen={menuOpen} setMenuOpen={setMenuOpen} />
        <main id="main-content" className="app-main">
          <PageTransition location={location} />
        </main>
        <SiteFooter siteSettings={siteSettings} navItems={navToRender} />
      </div>
    </SiteDataContext.Provider>
  )
}

function PageTransition({ location }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  )
}

function SiteHeader({ navItems, siteSettings, menuOpen, setMenuOpen }) {
  const [scrolled, setScrolled] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef(null)
  const location = useLocation()

  useEffect(() => {
    let ticking = false
    const onScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        setScrolled(window.scrollY > 8)
        ticking = false
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!moreOpen) return undefined
    function onDocClick(e) {
      if (moreRef.current && !moreRef.current.contains(e.target)) setMoreOpen(false)
    }
    function onKey(e) {
      if (e.key === 'Escape') {
        setMoreOpen(false)
        moreRef.current?.querySelector('button')?.focus()
      }
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [moreOpen])

  const { primary, more, contact } = useMemo(() => {
    const primary = []
    const more = []
    let contact = null
    navItems.forEach((item) => {
      const slug = slugOf(item.url)
      if (slug === CONTACT_SLUG) contact = item
      else if (PRIMARY_SLUGS.has(slug)) primary.push(item)
      else more.push(item)
    })
    return { primary, more, contact }
  }, [navItems])

  const moreActive = more.some((item) => isActivePath(location.pathname, toRoute(item.url)))

  return (
    <header className={`site-header ${scrolled ? 'is-scrolled' : ''}`}>
      <div className="container site-header__bar">
        {siteSettings?.logo_left && (
          <img className="site-header__crest" src={siteSettings.logo_left} alt="IIT Kharagpur" />
        )}

        <NavLink to="/" className="brand" end>
          {siteSettings?.site_logo && (
            <img className="brand__logo" src={siteSettings.site_logo} alt="" aria-hidden="true" />
          )}
          <span className="brand__text">
            <span className="brand__mark">CRTDH</span>
            <span className="brand__sub">IIT Kharagpur</span>
          </span>
        </NavLink>

        <nav className="site-nav" aria-label="Primary">
          <ul>
            {primary.map((item) => (
              <li key={item.id ?? item.label}>
                <NavLink to={toRoute(item.url)} end={toRoute(item.url) === '/'}>
                  {item.label}
                </NavLink>
              </li>
            ))}
            {more.length > 0 && (
              <li className="nav-more" ref={moreRef}>
                <button
                  type="button"
                  className={`nav-more__trigger ${moreActive ? 'active' : ''}`}
                  aria-haspopup="menu"
                  aria-expanded={moreOpen}
                  onClick={() => setMoreOpen((v) => !v)}
                >
                  More
                  <ChevronDown className={`nav-more__chevron ${moreOpen ? 'is-open' : ''}`} size={15} aria-hidden="true" />
                </button>
                <AnimatePresence>
                  {moreOpen && (
                    <motion.div
                      className="nav-more__panel"
                      role="menu"
                      initial={{ opacity: 0, y: -6, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -6, scale: 0.97 }}
                      transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
                    >
                      {more.map((item) => (
                        <NavLink key={item.id ?? item.label} role="menuitem" to={toRoute(item.url)}>
                          {item.label}
                        </NavLink>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            )}
          </ul>
        </nav>

        <div className="site-header__actions">
          {contact && (
            <NavLink to={toRoute(contact.url)} className="btn btn--accent btn--sm site-header__cta">
              {contact.label}
            </NavLink>
          )}
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            aria-label="Toggle navigation menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          </button>
        </div>

        {siteSettings?.logo_right && (
          <img className="site-header__crest site-header__crest--right" src={siteSettings.logo_right} alt="DSIR, Government of India" />
        )}
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            id="mobile-nav"
            className="mobile-nav"
            aria-label="Mobile"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <motion.ul
              initial="hidden"
              animate="show"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } } }}
            >
              {navItems.map((item) => (
                <motion.li
                  key={item.id ?? item.label}
                  variants={{ hidden: { opacity: 0, x: -12 }, show: { opacity: 1, x: 0 } }}
                >
                  <NavLink to={toRoute(item.url)} end={toRoute(item.url) === '/'}>
                    {item.label}
                  </NavLink>
                </motion.li>
              ))}
            </motion.ul>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  )
}

function isActivePath(pathname, route) {
  if (route === '/') return pathname === '/'
  return pathname.startsWith(route)
}

function SiteFooter({ siteSettings, navItems }) {
  const year = new Date().getFullYear()
  const socialLinks = siteSettings
    ? [
        { key: 'facebook', label: 'Facebook', href: siteSettings.facebook_url, Icon: FacebookIcon },
        { key: 'linkedin', label: 'LinkedIn', href: siteSettings.linkedin_url, Icon: LinkedinIcon },
        { key: 'instagram', label: 'Instagram', href: siteSettings.instagram_url, Icon: InstagramIcon },
        { key: 'twitter', label: 'Twitter', href: siteSettings.twitter_url, Icon: TwitterIcon },
      ].filter((link) => link.href)
    : []

  return (
    <footer className="site-footer">
      <div className="site-footer__glow" aria-hidden="true" />
      <div className="container site-footer__grid">
        <div className="site-footer__about">
          <span className="brand brand--footer">
            <span className="brand__mark">CRTDH</span>
          </span>
          <p>
            Common Research and Technology Development Hub on Affordable Healthcare — an initiative sponsored by
            DSIR, Government of India, hosted at IIT Kharagpur.
          </p>
          {socialLinks.length > 0 && (
            <ul className="social-links">
              {socialLinks.map(({ key, label, href, Icon }) => (
                <li key={key}>
                  <a href={href} target="_blank" rel="noreferrer" aria-label={label}>
                    <Icon size={16} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="site-footer__col">
          <h4>Explore</h4>
          <ul>
            {navItems.slice(0, 6).map((item) => (
              <li key={item.id ?? item.label}>
                <NavLink to={toRoute(item.url)}>{item.label}</NavLink>
              </li>
            ))}
          </ul>
        </div>

        <div className="site-footer__col">
          <h4>Contact</h4>
          {siteSettings ? (
            <ul className="footer-contact">
              {siteSettings.address && (
                <li>
                  <MapPin size={15} aria-hidden="true" />
                  <span>{siteSettings.address}</span>
                </li>
              )}
              {siteSettings.phone_primary && (
                <li>
                  <Phone size={15} aria-hidden="true" />
                  <span>
                    <a href={`tel:${siteSettings.phone_primary}`}>{siteSettings.phone_primary}</a>
                    {siteSettings.phone_secondary ? `, ${siteSettings.phone_secondary}` : ''}
                  </span>
                </li>
              )}
              {siteSettings.email_primary && (
                <li>
                  <Mail size={15} aria-hidden="true" />
                  <span>
                    <a href={`mailto:${siteSettings.email_primary}`}>{siteSettings.email_primary}</a>
                  </span>
                </li>
              )}
            </ul>
          ) : (
            <p className="footer-contact__empty">Contact details coming soon.</p>
          )}
        </div>
      </div>

      <div className="site-footer__bottom">
        <div className="container">
          &copy; {year} CRTDH, IIT Kharagpur. All rights reserved.
        </div>
      </div>
    </footer>
  )
}

// Nav item `url` can be a bare page slug (e.g. "about"), already a path
// (e.g. "/about"), or — for content seeded straight from the old static
// site — a legacy filename (e.g. "about.html", "index.html"); normalize
// any of those into a router-friendly path.
function toRoute(url) {
  if (!url) return '/'
  if (url.startsWith('http')) return url
  let slug = url.trim()
  if (slug === 'home' || slug === '/' || slug === 'index.html' || slug === '#') return '/'
  slug = slug.replace(/^\//, '').replace(/\.html?$/, '')
  return `/${slug}`
}
