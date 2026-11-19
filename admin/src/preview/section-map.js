// Where each registry section shows on the real public page (frontend/src/site).
//
// The public components carry no editor markup, and their page layouts (design lane) do not
// follow the registry's section order: one public block can show several sections, and a
// section can show on another page than its own. The canvas therefore tags the rendered
// page itself: each entry is [CSS selector, section id, optional item-id regex on
// aria-labelledby]. Selectors use the landmarks the public components already have
// (aria-labelledby / aria-label / BEM classes). Nested entries win on click because the
// canvas uses closest('[data-cms-section]').
//
// A section shown outside its own page is tagged with data-cms-elsewhere=<its page>, so a
// click opens it where it is edited. Sections with no visible block on a page stay editable
// from the panel. The shim (site-shim) tags itself and is left alone.

const LAYOUT = [
  ['.site-header', 'site.nav', 'Menu links'],
  ['.site-footer__contact', 'contact.details', 'Contact details'],
  ['.site-footer__social', 'site.social', 'Social links'],
  ['.site-footer__logos', 'site.logos', 'Logos'],
];

export const SECTION_MAP = {
  home: [
    ['section.hero', 'home.hero'],
    ['section.proof', 'enterprises.list', 'Enterprises'],
    ['section.work', 'innovations.list', 'Innovations'],
    ['section.manufacture', 'home.enterprises'],
    ['section.manufacture .facility-list', 'home.facilities'],
    ['section.community', 'home.rural'],
    ['section.news', 'home.news'],
    ['section.news .news__videos', 'home.videos'],
    ['section.visit', 'home.visit'],
  ],
  about: [
    ['section[aria-labelledby="about-programme"]', 'about.intro'],
    ['section[aria-labelledby="about-programme"] .split__side', 'about.ecosystem'],
    ['section[aria-labelledby="about-mission"]', 'about.intro'],
    ['section[aria-labelledby="about-focus"]', 'about.focus'],
    ['section[aria-labelledby="about-mission"] :has(> #about-focus)', 'about.focus'],
    ['section[aria-labelledby="about-objectives"]', 'about.support'],
    ['section[aria-labelledby="about-timeline"]', 'about.timeline'],
    ['section[aria-labelledby="about-pi"]', 'about.pi-note'],
    ['section[aria-labelledby="about-orgs"]', 'about.partners'],
  ],
  team: [['section[aria-label="Team members"]', 'team.members']],
  innovations: [
    ['section[aria-labelledby="spotlight"]', 'innovations.spotlight'],
    ['section[aria-label="All innovations"]', 'innovations.list'],
  ],
  facilities: [
    ['section[aria-labelledby="equipment"]', 'facilities.equipment'],
    ['section[aria-label="Manufacturing"]', 'facilities.photo-sections'],
  ],
  services: [['section[aria-labelledby="services-list"]', 'services.list']],
  product: [['section[aria-label="Products"]', 'product.list']],
  enterprises: [
    ['section[aria-labelledby="ent-engagement"]', 'home.enterprises', 'Enterprise engagement (Home page)'],
    ['section[aria-labelledby="ent-engagement"] .split__side', 'home.msme', 'MSME map (Home page)'],
    ['section[aria-labelledby="ent-directory"]', 'enterprises.list'],
    ['section[aria-label="Demonstration and training"]', 'enterprises.photo-sections'],
    ['section[aria-labelledby="ent-videos"]', 'enterprises.videos'],
  ],
  'social-impact': [
    ['section[aria-labelledby="impact-story"]', 'home.rural', 'Rural women (Home page)'],
    ['section[aria-labelledby^="block-"]', 'social-impact.photo-sections', null, /^block-(\d+)$/],
    ['section[aria-labelledby="impact-videos"]', 'social-impact.videos'],
  ],
  'covid-19': [
    ['section[aria-labelledby="covid-story"]', 'covid-19.photo-sections'],
    ['section[aria-labelledby="covid-photos"]', 'covid-19.photo-sections'],
    ['section[aria-labelledby="covid-videos"]', 'covid-19.videos'],
  ],
  media: [
    ['section.event', 'media.events', null, /^event-(\d+)$/],
    ['section[aria-labelledby="more-photos"]', 'media.gallery'],
    ['section[aria-label="Press and newsletters"]', 'media.coverage'],
  ],
  contact: [['section:has(.contact__details)', 'contact.details']],
};

/** The page that edits a section: "site" for site-wide sections, else the id's first part. */
export const ownerPage = (sectionId) => sectionId.split('.')[0];

/**
 * Tag the rendered public page in `root` for the canvas. Returns the number of tagged elements.
 * Leaves elements that already carry data-cms-section (the shim) untouched.
 */
export function tagSections(root, pageId, labels = {}) {
  if (root.querySelector('[data-cms-section]:not([data-cms-mapped])')) return 0; // shim markup
  for (const el of root.querySelectorAll('[data-cms-mapped]')) {
    for (const a of ['data-cms-section', 'data-cms-tag', 'data-cms-elsewhere', 'data-cms-item', 'data-cms-mapped']) el.removeAttribute(a);
  }
  const entries = [...(SECTION_MAP[pageId === 'site' ? 'home' : pageId] || []), ...LAYOUT];
  let n = 0;
  for (const [selector, sectionId, label, itemRe] of entries) {
    let found;
    try {
      found = root.querySelectorAll(selector);
    } catch {
      continue; // a selector the browser can't parse (e.g. :has in an old engine)
    }
    const owner = ownerPage(sectionId);
    for (const el of found) {
      if (el.hasAttribute('data-cms-section')) continue; // first entry for an element wins
      el.setAttribute('data-cms-section', sectionId);
      el.setAttribute('data-cms-mapped', '');
      el.setAttribute('data-cms-tag', labels[sectionId] || label || sectionId);
      if (owner !== pageId) el.setAttribute('data-cms-elsewhere', owner);
      const m = itemRe && (el.getAttribute('aria-labelledby') || '').match(itemRe);
      if (m) el.setAttribute('data-cms-item', m[1]);
      n += 1;
    }
  }
  return n;
}
