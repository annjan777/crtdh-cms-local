// Screenshot every admin screen at 1280/1024/390 against the mock.
// Needs `VITE_USE_MOCK=1 npx vite --port 3200` running. Usage: node scripts/tour.mjs [filter]
import { chromium } from '@playwright/test';

const BASE = 'http://localhost:3200';
const OUT = process.env.SHOTS_DIR || '/home/claude/team/screens/admin';
const WIDTHS = [1280, 1024, 390];
const only = process.argv[2];

async function password(page, user) {
  await page.goto(`${BASE}/`);
  await page.getByLabel('Username').fill(user);
  await page.getByLabel('Password').fill('local-test-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
}
async function signIn(page, user) {
  await password(page, user);
  await page.getByLabel('Code', { exact: true }).fill('246810');
  await page.getByRole('button', { name: 'Verify code' }).click();
  await page.waitForSelector('.topbar .brand');
}
const go = (path) => async (page, user = 'priya') => {
  await signIn(page, user);
  await page.goto(BASE + path);
};

const SCREENS = {
  'signin': async (page) => page.goto(`${BASE}/`),
  'signin-error': async (page) => {
    await page.goto(`${BASE}/`);
    await page.getByLabel('Username').fill('priya');
    await page.getByLabel('Password').fill('nope');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.getByText('don’t match').waitFor();
  },
  'mfa': async (page) => password(page, 'priya'),
  'enrol': async (page) => {
    await password(page, 'arjun');
    await page.getByRole('img', { name: /QR code/ }).waitFor();
  },
  'change-password': async (page) => {
    await signIn(page, 'meera').catch(() => {});
    await page.getByRole('heading', { name: 'Choose your own password' }).waitFor();
  },
  'editor-home': go('/pages/home'),
  'editor-hero': go('/pages/home?section=home.hero'),
  'editor-news': go('/pages/home?section=home.news'),
  'editor-team': go('/pages/team'),
  'editor-site-settings': go('/pages/site'),
  'preview': async (page) => {
    await go('/pages/home')(page);
    const link = page.getByRole('region', { name: 'Unpublished changes' }).getByRole('link', { name: 'Preview' });
    if (page.viewportSize().width >= 1024) await link.click();
    else await page.getByRole('button', { name: 'Preview page' }).click();
  },
  'review': go('/review'),
  'review-editor-role': async (page) => go('/review')(page, 'ravi'),
  'history': go('/history'),
  'users': async (page) => go('/users')(page, 'sita'),
  'users-add': async (page) => {
    await go('/users')(page, 'sita');
    await page.getByRole('button', { name: 'Add user' }).click();
  },
  'messages': async (page) => {
    await go('/messages')(page);
    await page.getByRole('list', { name: 'Messages' }).getByRole('button').first().click();
  },
  'shot-list': go('/shot-list'),
};

const browser = await chromium.launch();
for (const [name, run] of Object.entries(SCREENS)) {
  if (only && !name.includes(only)) continue;
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 600 ? 844 : 800 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    try {
      await run(page);
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${OUT}/${name}-${width}.png` });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      console.log(`${name}-${width}`, overflow ? 'OVERFLOW' : 'ok', errors.length ? `ERRORS: ${errors.join(' | ')}` : '');
    } catch (e) {
      console.log(`${name}-${width}`, 'FAILED', e.message.split('\n')[0]);
    }
    await ctx.close();
  }
}
await browser.close();
