// R-7 / F-07: the "Leave before your change is saved?" guard must fire for a
// real unsaved change and never for a visit with no change.
import { test, expect } from '@playwright/test';
import { signIn, canvas, panel } from './helpers.js';

const LEAVE = 'Leave before your change is saved?';
const hero = async (page) => {
  await canvas(page).locator('[data-cms-section="home.hero"]').click();
  return panel(page).getByRole('textbox', { name: 'Headline', exact: true });
};
const goHistory = (page) => page.getByRole('link', { name: /history/i }).first().click();
const draftKeys = (page) => page.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith('crtdh-draft:')));

test('open Home, change nothing, leave: no warning', async ({ page }) => {
  await signIn(page);
  await expect(canvas(page).locator('[data-cms-section="home.hero"]')).toBeVisible();
  await goHistory(page);
  await expect(page).toHaveURL(/\/history/);
  await expect(page.getByText(LEAVE)).toHaveCount(0);
});

test('change a field that cannot save yet, leave: warning appears', async ({ page }) => {
  await signIn(page);
  const headline = await hero(page);
  await headline.fill(''); // required: stays unsaved
  await goHistory(page);
  await expect(page.getByText(LEAVE)).toBeVisible();
  await page.getByRole('button', { name: 'Stay on this page' }).click();
  await expect(page).toHaveURL(/\/pages\/home/);
});

test('a kept draft that matches the CMS is dropped: no banner, no warning', async ({ page }) => {
  await signIn(page);
  const headline = await hero(page);
  const original = await headline.inputValue();
  await headline.fill(''); // cannot save, so it stays kept on this computer
  await goHistory(page);
  await page.getByRole('button', { name: 'Leave anyway' }).click();
  const [key] = await draftKeys(page);
  expect(key).toBeTruthy();
  // Make the leftover draft hold exactly what the CMS has (old base version).
  await page.evaluate(([k, v]) => {
    const d = JSON.parse(localStorage.getItem(k));
    const field = Object.keys(d.values)[0];
    localStorage.setItem(k, JSON.stringify({ values: { [field]: v }, base_version: 1, at: new Date().toISOString() }));
  }, [key, original]);
  // Back into the editor through the app's own Pages menu (the mock CMS keeps its data).
  await page.getByRole('link', { name: 'CRTDH website' }).click();
  await expect(canvas(page).locator('[data-cms-section="home.hero"]')).toBeVisible();
  await expect(page.getByText(/Restored \d+ unsaved/)).toHaveCount(0);
  const left = await draftKeys(page);
  expect(left).toEqual([]);
  await goHistory(page);
  await expect(page).toHaveURL(/\/history/);
  await expect(page.getByText(LEAVE)).toHaveCount(0);
});

test('a kept draft that cannot save: banner says so, Discard clears it, then no warning', async ({ page }) => {
  await signIn(page);
  const headline = await hero(page);
  await headline.fill('');
  await goHistory(page);
  await page.getByRole('button', { name: 'Leave anyway' }).click();
  await page.goto('/pages/home');
  await expect(page.getByText(/Restored 1 unsaved change from an earlier visit/)).toBeVisible();
  await expect(page.getByText(/can’t save as it is/)).toBeVisible();
  await page.getByRole('button', { name: 'Discard it' }).click();
  await expect(page.getByText(/Restored \d+ unsaved/)).toHaveCount(0);
  expect(await draftKeys(page)).toEqual([]);
  await goHistory(page);
  await expect(page).toHaveURL(/\/history/);
  await expect(page.getByText(LEAVE)).toHaveCount(0);
});
