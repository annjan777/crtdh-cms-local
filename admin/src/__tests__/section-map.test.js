// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { SECTION_MAP, ownerPage, tagSections } from '../preview/section-map.js';

const html = `
<header class="site-header"><img class="site-header__crest" alt=""></header>
<main>
  <section data-block="home.hero" class="hero"></section>
  <section data-block="home.enterprises" class="section"><div data-block="home.videos" class="home-split__right"></div></section>
</main>
<footer class="site-footer"><ul class="social-links"></ul></footer>`;

describe('section map', () => {
  it('tags real public markup with section ids, nested entries, and the owning page', () => {
    document.body.innerHTML = html;
    const n = tagSections(document.body, 'home', { 'home.hero': 'Hero' });
    expect(n).toBe(6);
    const hero = document.querySelector('.hero');
    expect(hero.dataset.cmsSection).toBe('home.hero');
    expect(hero.dataset.cmsTag).toBe('Hero');
    expect(hero.hasAttribute('data-cms-elsewhere')).toBe(false);
    expect(document.querySelector('.home-split__right').dataset.cmsSection).toBe('home.videos');
    expect(document.querySelector('.site-header__crest').dataset.cmsSection).toBe('site.logos');
    expect(document.querySelector('.site-header').dataset.cmsElsewhere).toBe('site');
  });

  it('marks a section shown on another page with the page that edits it', () => {
    document.body.innerHTML = '<section data-block="social-impact.story"></section>';
    tagSections(document.body, 'social-impact');
    const el = document.querySelector('section');
    expect(el.dataset.cmsSection).toBe('home.rural');
    expect(el.dataset.cmsElsewhere).toBe('home');
  });

  it('re-tags cleanly and leaves markup that is already tagged alone', () => {
    document.body.innerHTML = html;
    tagSections(document.body, 'home');
    tagSections(document.body, 'home');
    expect(document.querySelectorAll('[data-cms-section="home.hero"]')).toHaveLength(1);
    document.body.innerHTML = '<section data-cms-section="home.hero" class="hero"></section>';
    expect(tagSections(document.body, 'home')).toBe(0);
  });

  it('maps only real registry sections of known pages', () => {
    const known = new Set(['home', 'about', 'team', 'innovations', 'facilities', 'services', 'product', 'enterprises',
      'social-impact', 'covid-19', 'research', 'research-translation', 'media', 'contact', 'site']);
    for (const [page, entries] of Object.entries(SECTION_MAP)) {
      expect(known.has(page)).toBe(true);
      for (const [, id] of entries) expect(known.has(ownerPage(id))).toBe(true);
    }
  });
});

import { autoDescription } from '../editor/fields/ImageField.jsx';

describe('photo description is filled in automatically', () => {
  it('uses the section title, else a readable file name', () => {
    expect(autoDescription({ values: { title: '  Health camp at Salboni ' } }, { name: 'IMG_1.jpg' })).toBe('Health camp at Salboni');
    expect(autoDescription({ values: {} }, { name: 'IIT-Kharagpur_at_Golden Hour.png' })).toBe('IIT Kharagpur at Golden Hour');
    expect(autoDescription({ values: {} }, null)).toBe('Photo');
  });
});
