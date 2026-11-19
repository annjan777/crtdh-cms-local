import { describe, expect, it } from 'vitest';
import { navPages, SITE_PAGE_ID } from '../shell/ChangesContext.jsx';

// The real GET /api/v1/cms/pages/ (backend/apps/publishing/views.py PagesView) puts the site-wide sections under
// `globals`; the admin used to look for a page with id "site", which only the old mock had (QA: B4).
const REAL = {
  pages: [{ id: 'home', path: '/', title: 'Home', has_changes: false, sections: [{ id: 'home.hero', label: 'Hero', kind: 'collection', resource: 'hero-slides' }] }],
  globals: { has_changes: true, sections: [{ id: 'site.nav', label: 'Menu links', kind: 'collection', resource: 'nav-items' }] },
};

describe('nav pages from GET /cms/pages/', () => {
  it('turns globals into the "Header & footer" entry the nav shows', () => {
    const out = navPages(REAL);
    expect(out.map((p) => p.id)).toEqual(['home', SITE_PAGE_ID]);
    expect(out[1]).toEqual({ id: 'site', path: null, title: 'Header & footer', has_changes: true, sections: REAL.globals.sections });
  });
  it('works without globals and never lists "site" twice', () => {
    expect(navPages({ pages: REAL.pages })).toEqual(REAL.pages);
    expect(navPages({ ...REAL, pages: [...REAL.pages, { id: 'site', path: null, title: 'x', sections: [] }] }).filter((p) => p.id === 'site')).toHaveLength(1);
  });
});
