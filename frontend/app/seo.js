import { SEO } from '../src/site/seo.js'

/** Per-page <title>, description, canonical, Open Graph and the build marker. */
export function pageMeta(id, { matches, data }) {
  const root = matches.find((m) => m.id === 'root')?.data || {}
  const site = root.meta?.site_url || 'https://crtdh.iitkgp.ac.in'
  const s = SEO[id] || SEO.notfound
  const url = `${site}${s.path === '/' ? '/' : s.path}`
  const ogImage = (data && s.image ? s.image(data) : null) || root.meta?.og_image
  const abs = (u) => (u && !/^https?:/.test(u) ? `${site}${u}` : u)
  const tags = [
    { title: s.title },
    { name: 'description', content: s.description },
    { property: 'og:type', content: 'website' },
    { property: 'og:site_name', content: 'CRTDH, IIT Kharagpur' },
    { property: 'og:title', content: s.title },
    { property: 'og:description', content: s.description },
    { property: 'og:url', content: url },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'crtdh-build', content: root.meta?.snapshot_id || '' },
    { name: 'crtdh-snapshot', content: root.meta?.snapshot_id || '' },
  ]
  if (id !== 'notfound') tags.push({ tagName: 'link', rel: 'canonical', href: url })
  else tags.push({ name: 'robots', content: 'noindex' })
  if (ogImage) tags.push({ property: 'og:image', content: abs(ogImage) })
  if (id === 'home') tags.push({ 'script:ld+json': organizationLd(root, site) })
  if (id === 'media' && data) {
    for (const ev of data.collections?.['media-events'] || []) {
      if (ev.event_date) tags.push({ 'script:ld+json': eventLd(ev, root, site) })
    }
  }
  return tags
}

function organizationLd(root, site) {
  const st = root.singletons?.['site-settings'] || {}
  const abs = (u) => (u && !/^https?:/.test(u) ? `${site}${u}` : u)
  return {
    '@context': 'https://schema.org',
    '@type': 'ResearchOrganization',
    name: 'Common Research and Technology Development Hub (CRTDH) on Affordable Healthcare',
    alternateName: 'CRTDH, IIT Kharagpur',
    url: `${site}/`,
    logo: abs(st.site_logo) || undefined,
    email: st.email_primary || undefined,
    telephone: st.phone_primary || undefined,
    address: st.address ? { '@type': 'PostalAddress', streetAddress: st.address, addressCountry: 'IN' } : undefined,
    parentOrganization: { '@type': 'CollegeOrUniversity', name: 'Indian Institute of Technology Kharagpur', url: 'https://www.iitkgp.ac.in/' },
    funder: { '@type': 'GovernmentOrganization', name: 'Department of Scientific and Industrial Research, Government of India' },
    sameAs: [st.facebook_url, st.linkedin_url, st.instagram_url, st.twitter_url].filter(Boolean),
  }
}

function eventLd(ev, root, site) {
  const st = root.singletons?.['site-settings'] || {}
  const img = (ev.images || [])[0]?.image
  return {
    '@context': 'https://schema.org',
    '@type': 'Event',
    name: ev.title,
    startDate: ev.event_date,
    description: ev.description || undefined,
    image: img ? (/^https?:/.test(img) ? img : `${site}${img}`) : undefined,
    url: `${site}/media#${ev.slug}`,
    eventStatus: 'https://schema.org/EventScheduled',
    eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
    location: { '@type': 'Place', name: 'CRTDH, IIT Kharagpur', address: st.address || 'IIT Kharagpur' },
    organizer: { '@type': 'Organization', name: 'CRTDH, IIT Kharagpur', url: `${site}/` },
  }
}
