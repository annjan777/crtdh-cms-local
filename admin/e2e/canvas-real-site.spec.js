import { expect, test } from '@playwright/test';
import { canvas, panel, signIn } from './helpers.js';

// The canvas renders the real public components (frontend/src/site via the @site alias) and
// tags their blocks with registry section ids (src/preview/section-map.js).
const PAGES = {
  home: ['home.hero', 'home.news'],
  about: ['about.intro'],
  team: ['team.members'],
  innovations: ['innovations.list'],
  facilities: ['facilities.equipment'],
  services: ['services.list'],
  product: ['product.list'],
  enterprises: ['enterprises.list'],
  'social-impact': ['social-impact.photo-sections'],
  'covid-19': ['covid-19.photo-sections'],
  media: ['media.events'],
  contact: ['contact.details'],
};

test('every page renders the real public site with clickable sections', async ({ page }) => {
  test.setTimeout(120_000); // twelve pages
  await signIn(page, 'priya');
  for (const [pageId, ids] of Object.entries(PAGES)) {
    await page.goto(`/pages/${pageId}`);
    const frame = canvas(page);
    await expect(frame.locator('.site-header')).toBeVisible(); // the real public Layout
    for (const id of ids) await expect(frame.locator(`[data-cms-section="${id}"]`).first(), `${pageId}: ${id}`).toBeVisible();
  }
});

test('a section shown on another page opens where it is edited', async ({ page }) => {
  // In the restored design the Social impact page shows the "Rural women" story, which is edited on Home.
  await signIn(page, 'priya', '/pages/social-impact');
  await canvas(page).locator('[data-cms-section="home.rural"]').first().click();
  await expect(page).toHaveURL(/\/pages\/home\?section=home\.rural/);
  await expect(panel(page).getByRole('heading', { level: 2 }).first()).toBeVisible();
});
