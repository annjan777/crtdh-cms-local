import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canvas, mock, panel, signIn } from './helpers.js';

const fixtures = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures');

test('storyboard: edit hero → saved → preview → review → publish → live', async ({ page }) => {
  await signIn(page, 'priya');
  await expect(page.getByText('2 unpublished changes on 2 pages')).toBeVisible();
  // 1-2: click the hero on the real page.
  await canvas(page).locator('[data-cms-section="home.news"]').click();
  await expect(panel(page).getByRole('heading', { name: 'News ticker', level: 2 })).toBeVisible();
  await canvas(page).locator('[data-cms-section="home.hero"]').click();
  await expect(panel(page).getByRole('heading', { name: 'Hero', level: 2 })).toBeVisible();
  // 4: type a headline; it shows on the canvas and autosaves.
  const headline = panel(page).getByRole('textbox', { name: 'Headline', exact: true });
  await headline.fill('Affordable diagnostics for India');
  await expect(canvas(page).locator('[data-cms-section="home.hero"] h1')).toContainText('Affordable diagnostics for India');
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
  await expect(page.getByText('3 unpublished changes on 2 pages')).toBeVisible();
  // Preview full screen.
  await page.getByRole('link', { name: 'Preview' }).click();
  await expect(page.getByText('Includes unpublished changes. Not live yet.')).toBeVisible();
  await expect(page.frameLocator('iframe[title="Preview of the Home page"]').locator('h1').first()).toContainText('Affordable diagnostics for India');
  await page.getByRole('button', { name: 'Close preview' }).click();
  // 5: review.
  await page.getByRole('region', { name: 'Unpublished changes' }).getByRole('link', { name: 'Review & publish' }).click();
  await expect(page.getByRole('heading', { name: 'Review & publish', level: 1 })).toBeVisible();
  const change = page.locator('.change', { hasText: 'Affordable diagnostics for India' });
  await expect(change).toContainText('Priya Sen in the editor');
  await expect(change.locator('del')).toContainText('Common Research &');
  await expect(page.locator('.change', { hasText: 'Principal Investigator, CRTDH' })).toContainText('through Claude');
  // 6: publish and watch it go live.
  await page.getByRole('button', { name: 'Publish 3 changes' }).click();
  await expect(page.locator('.steps li[aria-current="step"]')).toContainText(/Queued|Building/);
  await expect(page.locator('.steps li[aria-current="step"]')).toContainText('Uploading to the server', { timeout: 10_000 });
  await expect(page.getByText(/Live at \d\d:\d\d/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 'Nothing to publish' })).toBeVisible();
  await expect(page.getByText('Everything is live')).toBeVisible();
});

test('stale version: a save based on an old version shows who changed it and never overwrites', async ({ page }) => {
  await signIn(page, 'ravi', '/pages/home?section=home.hero');
  const headline = panel(page).getByRole('textbox', { name: 'Headline', exact: true });
  await expect(headline).toHaveValue('Common Research &');
  // Priya edits the same slide in another tab.
  await mock(page, 'otherUserEdits', 'hero-slides', 18, { heading: 'Priya’s headline' }, 'Priya Sen');
  await headline.fill('Ravi’s headline');
  const box = panel(page).getByRole('alert').filter({ hasText: 'changed this' });
  await expect(box).toContainText('Priya Sen changed this');
  await expect(box).toContainText('Ravi’s headline');
  await expect(panel(page).getByText('Not saved · changed by someone else')).toBeVisible();
  const db = await mock(page, 'state');
  expect(db.rows['hero-slides']['18'].heading).toBe('Priya’s headline');
  await box.getByRole('button', { name: 'Reload section' }).click();
  await expect(headline).toHaveValue('Priya’s headline');
});

test('upload rejection: a hero photo under 1600 px is refused and the old photo kept', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  const current = panel(page).locator('.image-field img').first(); // the focus picker's photo
  const before = await current.getAttribute('src');
  await panel(page).locator('input[type=file]').first().setInputFiles(path.join(fixtures, 'photo-1200.png'));
  await expect(panel(page).getByText('This photo is 1200 px wide. Photos in this section need at least 1600 px')).toBeVisible();
  await expect(panel(page).getByRole('link', { name: 'See the shot list' }).first()).toBeVisible();
  expect(await current.getAttribute('src')).toBe(before);
  await expect(panel(page).getByRole('button', { name: 'Save photo' })).toHaveCount(0);
});

// The photo field was simplified on 2026-11-19 (owner request): no description box. The rule this test guards
// is unchanged: a photo is never saved without a description for screen readers. It is written automatically
// from the section's own text. (On 2026-11-20 the owner asked for the hero focus point back: e2e/focus-point.spec.js.)
test('a new photo is saved with an automatic description, never without one', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  const heading = await panel(page).getByRole('textbox', { name: 'Headline', exact: true }).inputValue();
  expect(heading.trim()).not.toBe('');
  await panel(page).locator('input[type=file]').first().setInputFiles(path.join(fixtures, 'photo-2400.jpg'));
  await expect(panel(page).getByText('New photo, not saved yet.')).toBeVisible();
  await expect(panel(page).getByLabel('Photo description')).toHaveCount(0);
  let db = await mock(page, 'state');
  expect(db.rows['hero-slides']['18'].image).toContain('/api/v1/media/'); // nothing saved before Save photo
  await panel(page).getByRole('button', { name: 'Save photo' }).click();
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
  db = await mock(page, 'state');
  expect(db.rows['hero-slides']['18'].image).toMatch(/^data:image/);
  expect(db.rows['hero-slides']['18'].alt_text).toBe(heading.trim());
});

test('only the hero photo offers a focus point; other photos are a plain preview', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  await expect(panel(page).locator('.focus-picker')).toBeVisible();
  await page.goto('/pages/facilities?section=facilities.equipment');
  await expect(panel(page).locator('.image-field').first()).toBeVisible();
  await expect(panel(page).locator('.focus-picker')).toHaveCount(0);
});

test('collections: add, hide and reorder with the keyboard', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.news');
  const list = panel(page).getByRole('list', { name: 'News ticker in order' });
  const first = await list.locator('.item-label').first().textContent();
  // Keyboard reorder: Space, ArrowDown, Space on the first handle.
  await list.locator('.drag-handle').first().focus();
  await page.keyboard.press('Space');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Space');
  await expect(list.locator('.item-label').nth(1)).toHaveText(first);
  // Add a news line: new items start hidden.
  await panel(page).getByRole('button', { name: 'Add news line' }).click();
  await expect(list.locator('.item-row').last()).toContainText('Hidden');
  await panel(page).getByRole('textbox', { name: 'News line' }).fill('Eye camp at Kharagpur on 2 December');
  // Click the switch as people do (its label); the input itself is a 1px hidden control.
  await panel(page).locator('label.switch', { hasText: 'Shown on site' }).click();
  await expect(panel(page).getByRole('switch', { name: 'Shown on site' })).toBeChecked();
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
  await expect(canvas(page).locator('[data-cms-section="home.news"]')).toContainText('Eye camp at Kharagpur');
});

test('validation: required and too-long fields show a fix on blur, not while typing', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  const headline = panel(page).getByRole('textbox', { name: 'Headline', exact: true });
  await headline.fill('');
  await expect(panel(page).getByText('Enter headline.')).toHaveCount(0);
  await headline.blur();
  await expect(panel(page).getByText('Enter headline.')).toBeVisible();
  await headline.fill('x'.repeat(45));
  await headline.blur();
  await expect(panel(page).getByText('Shorten to 40 characters (now 45).')).toBeVisible();
  await expect(panel(page).getByText('45 / 40')).toBeVisible();
});

test('offline: text is kept locally and saved when the connection returns', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.objective');
  await mock(page, 'setOffline', true);
  await panel(page).getByLabel('Statement').fill('Health access for everyone, everywhere.');
  await expect(page.getByText('You’re offline.')).toBeVisible();
  await expect(panel(page).getByText('Offline · kept on this computer')).toBeVisible();
  const kept = await page.evaluate(() => localStorage.getItem('crtdh-draft:1:home-page:1'));
  expect(kept).toContain('Health access for everyone');
  await mock(page, 'setOffline', false);
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('crtdh-draft:1:home-page:1'))).toBeNull();
});

test('session expiry: sign in again and the unsaved text is restored', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.objective');
  await expect(panel(page).getByLabel('Statement')).toBeEditable();
  await page.waitForTimeout(800); // let the section's first fetches settle
  await mock(page, 'expireSession');
  await panel(page).getByLabel('Statement').fill('Kept across sign-in.');
  await expect(page.getByRole('heading', { name: 'Sign in again' })).toBeVisible();
  await page.getByLabel('Username').fill('priya');
  await page.getByLabel('Password').fill('local-test-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Code', { exact: true }).fill('246810');
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByText(/Restored 1 unsaved change/)).toBeVisible();
  await expect(panel(page).getByLabel('Statement')).toHaveValue('Kept across sign-in.');
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
});

test('below 1024 px: section list and fields, preview full screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page, 'priya');
  await expect(page.getByRole('list', { name: 'Sections on this page' })).toBeVisible();
  await expect(page.locator('iframe[title*="Select a section"]')).toHaveCount(0);
  await page.getByRole('button', { name: /Visit us/ }).click();
  await expect(panel(page).getByRole('heading', { name: 'Visit us', level: 2 })).toBeVisible();
  await page.getByRole('button', { name: 'Open pages menu' }).click();
  await page.getByRole('dialog').getByRole('link', { name: 'Team' }).click();
  await expect(page.getByRole('heading', { name: 'Team', level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'Preview page' }).click();
  // The restored design titles the Team page from its CMS banner ("PI, Co-PIs and Research Team").
  await expect(page.frameLocator('iframe[title="Preview of the Team page"]').locator('h1')).toContainText(/Team/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
