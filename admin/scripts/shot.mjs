// Ad-hoc screenshot helper: node scripts/shot.mjs <name> <width> [user] [path] [actions...]
import { chromium } from '@playwright/test';
const [name, width = '1280', user = 'priya', path = '/pages/home', ...acts] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: Number(width), height: Number(width) < 600 ? 844 : 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
await page.goto('http://localhost:3200/');
if (user !== 'none') {
  await page.getByLabel('Username').fill(user);
  await page.getByLabel('Password').fill('local-test-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Code', { exact: true }).fill('246810');
  await page.getByRole('button', { name: 'Verify code' }).click();
  await page.waitForSelector('.topbar .brand');
}
await page.goto('http://localhost:3200' + path);
await page.waitForTimeout(2000);
for (const a of acts) { await eval(`(async()=>{${a}})()`); await page.waitForTimeout(800); }
await page.screenshot({ path: `/home/claude/team/screens/admin/${name}-${width}.png` });
const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
console.log(name, width, 'overflow:', overflow, errors.length ? 'ERRORS: ' + errors.join(' | ') : '');
await browser.close();
