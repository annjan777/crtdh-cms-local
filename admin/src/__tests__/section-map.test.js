// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { SECTION_MAP, ownerPage, tagSections } from '../preview/section-map.js';

const html = `
<header class="site-header"></header>
<main>
  <section class="section hero"></section>
  <section class="section proof"></section>
  <section class="section manufacture"><ul class="facility-list"><li>x</li></ul></section>
</main>
<footer><div class="site-footer__social"></div></footer>`;

describe('section map', () => {
  it('tags real public markup with section ids, nested entries, and the owning page', () => {
    document.body.innerHTML = html;
    const n = tagSections(document.body, 'home', { 'home.hero': 'Hero' });
    expect(n).toBe(6);
    const hero = document.querySelector('.hero');
    expect(hero.dataset.cmsSection).toBe('home.hero');
    expect(hero.dataset.cmsTag).toBe('Hero');
    expect(hero.hasAttribute('data-cms-elsewhere')).toBe(false);
    expect(document.querySelector('.proof').dataset.cmsElsewhere).toBe('enterprises');
    expect(document.querySelector('.facility-list').dataset.cmsSection).toBe('home.facilities');
    expect(document.querySelector('.site-header').dataset.cmsElsewhere).toBe('site');
  });

  it('re-tags cleanly and leaves the shim alone', () => {
    document.body.innerHTML = html;
    tagSections(document.body, 'home');
    tagSections(document.body, 'home');
    expect(document.querySelectorAll('[data-cms-section="home.hero"]')).toHaveLength(1);
    document.body.innerHTML = '<section data-cms-section="home.hero" class="hero"></section>';
    expect(tagSections(document.body, 'home')).toBe(0);
  });

  it('reads item ids from aria-labelledby', () => {
    document.body.innerHTML = '<section class="section event" aria-labelledby="event-7"></section>';
    tagSections(document.body, 'media');
    expect(document.querySelector('.event').dataset.cmsItem).toBe('7');
  });

  it('maps only real registry sections of known pages', () => {
    const known = new Set(['home', 'about', 'team', 'innovations', 'facilities', 'services', 'product', 'enterprises',
      'social-impact', 'covid-19', 'media', 'contact', 'site']);
    for (const [page, entries] of Object.entries(SECTION_MAP)) {
      expect(known.has(page)).toBe(true);
      for (const [, id] of entries) expect(known.has(ownerPage(id))).toBe(true);
    }
  });
});
