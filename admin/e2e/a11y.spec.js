import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { PASSWORD, signIn } from './helpers.js';

// Screen-reader/keyboard pass: axe (WCAG 2.1 A/AA) on every screen, plus a
// keyboard walk of the editor.
const SCREENS = [
  ['sign in', null, '/'],
  ['editor', 'priya', '/pages/home?section=home.hero'],
  ['collection', 'priya', '/pages/home?section=home.news'],
  ['review', 'priya', '/review'],
  ['history', 'priya', '/history'],
  ['users', 'sita', '/users'],
  ['shot list', 'priya', '/shot-list'],
];

for (const [name, user, path] of SCREENS) {
  test(`axe: ${name}`, async ({ page }) => {
    if (user) await signIn(page, user, path);
    else await page.goto(path);
    await page.waitForTimeout(800);
    // The canvas iframe is the frontend lane's public page; it has its own audit.
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).exclude('iframe').analyze();
    const issues = res.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`);
    expect(issues).toEqual([]);
  });
}

// Phones (QA wave 2 D9): the user button lost its name when .user-name is hidden, and /shot-list had a
// scroll region with nothing focusable in it.
for (const [name, user, path] of SCREENS) {
  test(`axe at 375 px: ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    if (user) await signIn(page, user, path);
    else await page.goto(path);
    await page.waitForTimeout(800);
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).exclude('iframe').analyze();
    const issues = res.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`);
    expect(issues).toEqual([]);
  });
}

test('keyboard: skip link, page nav, section list and fields are reachable with a visible focus ring', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused();
  await page.keyboard.press('Enter');
  // Section 2 from the page navigation by keyboard.
  const news = page.getByRole('link', { name: /News ticker/ }).or(page.getByRole('button', { name: /News ticker/ })).first();
  await news.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('aside.field-panel').getByRole('heading', { name: 'News ticker', level: 2 })).toBeVisible();
  const ring = await page.evaluate(() => {
    const el = document.activeElement;
    const cs = getComputedStyle(el);
    return cs.outlineStyle !== 'none' || cs.boxShadow !== 'none';
  });
  expect(ring).toBe(true);
});

test('keyboard: dialogs trap focus and Escape returns focus to the trigger', async ({ page }) => {
  await signIn(page, 'sita', '/users');
  const trigger = page.getByRole('button', { name: 'Add user' });
  await trigger.focus();
  await page.keyboard.press('Enter');
  const dlg = page.getByRole('dialog', { name: 'Add a user' });
  await expect(dlg.getByLabel('Full name')).toBeFocused();
  for (let i = 0; i < 12; i += 1) await page.keyboard.press('Tab');
  expect(await dlg.evaluate((d) => d.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('sign-in errors are announced', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Username').fill('priya');
  await page.getByLabel('Password').fill(`${PASSWORD}x`);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert').or(page.locator('[role=status]')).filter({ hasText: 'don’t match' })).toBeVisible();
});
