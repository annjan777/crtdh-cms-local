// Public pages and the snapshot data each one needs. Mirrors the backend
// section registry page ids (contracts §2). The same map drives the route
// loaders (build), the build guard and the admin preview.
export const PAGES = [
  { id: 'home', path: '/', title: 'Home' },
  { id: 'about', path: '/about/', title: 'About' },
  { id: 'team', path: '/team/', title: 'Team' },
  { id: 'innovations', path: '/innovations/', title: 'Innovations' },
  { id: 'facilities', path: '/facilities/', title: 'Facilities' },
  { id: 'services', path: '/services/', title: 'Services' },
  { id: 'product', path: '/product/', title: 'Product' },
  { id: 'enterprises', path: '/enterprises/', title: 'Enterprises' },
  { id: 'social-impact', path: '/social-impact/', title: 'Social Impact' },
  { id: 'covid-19', path: '/covid-19/', title: 'Covid-19' },
  { id: 'media', path: '/media/', title: 'Media' },
  { id: 'contact', path: '/contact/', title: 'Contact' },
]

export const PAGE_PATHS = PAGES.map((p) => p.path)

// Data every page shows in the header and footer.
export const LAYOUT_NEEDS = {
  singletons: ['site-settings'],
  collections: ['nav-items'],
}

export const PAGE_NEEDS = {
  home: {
    singletons: ['home-page', 'site-settings'],
    collections: ['hero-slides', 'enterprises', 'products', 'innovations', 'news-items', 'documents', 'media-events', 'equipment', 'team-members'],
  },
  about: {
    singletons: ['about-page'],
    collections: ['focus-areas', 'objective-rows', 'timeline-entries'],
  },
  team: { singletons: [], collections: ['team-categories', 'team-members'] },
  innovations: { singletons: [], collections: ['innovations', 'project-slides'] },
  facilities: { singletons: [], collections: ['equipment', 'image-grid-blocks'] },
  services: { singletons: ['home-page'], collections: ['services'] },
  product: { singletons: [], collections: ['products'] },
  enterprises: { singletons: ['home-page'], collections: ['enterprises', 'image-grid-blocks', 'video-blocks'] },
  'social-impact': { singletons: ['home-page'], collections: ['image-grid-blocks', 'video-blocks'] },
  'covid-19': { singletons: [], collections: ['image-grid-blocks', 'video-blocks'] },
  media: { singletons: [], collections: ['media-events', 'gallery-images', 'media-coverage-links', 'documents'] },
  contact: { singletons: ['site-settings'], collections: [] },
  notfound: { singletons: [], collections: [] },
}

// Every collection and singleton the public build reads. The build fails if any is
// missing from the snapshot (a missing list is a build error, never an empty section).
export const REQUIRED = (() => {
  const s = new Set(LAYOUT_NEEDS.singletons)
  const c = new Set(LAYOUT_NEEDS.collections)
  for (const n of Object.values(PAGE_NEEDS)) {
    n.singletons.forEach((x) => s.add(x))
    n.collections.forEach((x) => c.add(x))
  }
  return { singletons: [...s], collections: [...c] }
})()

/** Pick the part of a snapshot-shaped object a page needs (same shape). */
export function selectData(snapshot, needs) {
  const out = { singletons: {}, collections: {}, media: {} }
  for (const k of needs.singletons) out.singletons[k] = snapshot.singletons?.[k] ?? null
  for (const k of needs.collections) out.collections[k] = snapshot.collections?.[k] ?? []
  // Only the media entries the selected rows reference, to keep each page's HTML small.
  const media = snapshot.media || {}
  if (Object.keys(media).length) {
    const text = JSON.stringify([out.singletons, out.collections])
    for (const [url, info] of Object.entries(media)) if (text.includes(`"${url}"`)) out.media[url] = info
  }
  return out
}
