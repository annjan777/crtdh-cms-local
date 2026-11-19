// Where each registry section shows on the real public page (frontend/src/site).
//
// The public components carry no editor markup, and their page layouts (design lane) do not
// follow the registry's section order: one public block can show several sections, and a
// section can show on another page than its own. The canvas therefore tags the rendered
// page itself: each entry is [CSS selector, section id, optional item-id regex on
// aria-labelledby]. Page blocks are found by their data-block attribute; the header and footer by
// their class names. Nested entries win on click because the
// canvas uses closest('[data-cms-section]').
//
// A section shown outside its own page is tagged with data-cms-elsewhere=<its page>, so a
// click opens it where it is edited. Sections with no visible block on a page stay editable
// from the panel. Markup that already carries data-cms-section is left alone.

const LAYOUT = [
  ['.site-header__crest', 'site.logos', 'Logos'],
  ['.brand__logo', 'site.logos', 'Logos'],
  ['.site-header', 'site.nav', 'Menu links'],
  ['.site-footer .social-links', 'site.social', 'Social links'],
  ['.site-footer__col:last-of-type', 'contact.details', 'Contact details'],
];

// Page blocks carry a neutral data-block="<section id>" attribute (frontend/src/site/pages/*).
const block = (id, label) => [`[data-block="${id}"]`, id, label];

export const SECTION_MAP = {
  home: [
    block('home.hero'), block('home.news'), block('home.membership'), block('home.objective'),
    block('home.enterprises'), block('home.rural'), block('home.facilities'), block('home.videos'), block('home.visit'),
  ],
  about: [
    block('about.intro'), block('about.focus'), block('about.support'), block('about.ecosystem'),
    block('about.timeline'), block('about.pi-note'), block('about.partners'),
  ],
  team: [block('team.members')],
  innovations: [block('innovations.spotlight'), block('innovations.list')],
  facilities: [block('facilities.equipment'), block('facilities.photo-sections')],
  services: [block('services.list')],
  product: [block('product.list')],
  enterprises: [block('enterprises.list'), block('enterprises.photo-sections'), block('enterprises.videos')],
  'social-impact': [
    ['[data-block="social-impact.story"]', 'home.rural', 'Rural women (Home page)'],
    block('social-impact.photo-sections'), block('social-impact.videos'),
  ],
  'covid-19': [
    ['[data-block="covid-19.story"]', 'covid-19.photo-sections'],
    block('covid-19.photo-sections'), block('covid-19.videos'),
  ],
  media: [block('media.events'), block('media.gallery'), block('media.coverage'), block('media.documents')],
  contact: [block('contact.details')],
};

/** The page that edits a section: "site" for site-wide sections, else the id's first part. */
export const ownerPage = (sectionId) => sectionId.split('.')[0];

/**
 * Tag the rendered public page in `root` for the canvas. Returns the number of tagged elements.
 * Leaves elements that already carry data-cms-section untouched.
 */
export function tagSections(root, pageId, labels = {}) {
  if (root.querySelector('[data-cms-section]:not([data-cms-mapped])')) return 0; // tagged by its author
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
