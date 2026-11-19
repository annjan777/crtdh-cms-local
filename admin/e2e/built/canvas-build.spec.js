import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { canvas, signIn } from '../helpers.js';

// QA wave 2 D6: with frontend/node_modules present the built canvas loaded a second React and stayed blank
// ("Cannot read properties of null (reading 'useRef')"). Checks the production build renders real page text.
const here = path.dirname(fileURLToPath(import.meta.url));
const frontendModules = path.resolve(here, '../../../frontend/node_modules/react');

test('built canvas renders the real public page', async ({ page }) => {
  test.skip(!fs.existsSync(frontendModules), 'needs frontend/node_modules (the setup that loaded two Reacts)');
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(e.message));
  await signIn(page, 'priya', '/pages/home');
  const frame = canvas(page);
  await expect(frame.locator('.site-header')).toBeVisible(); // real Layout, not the shim
  await expect(frame.locator('.s-root')).toHaveCount(0);
  await expect(frame.locator('#preview-root')).not.toBeEmpty();
  await expect(frame.locator('[data-cms-section="home.hero"]').first()).toBeVisible();
  expect((await frame.locator('body').innerText()).trim().length).toBeGreaterThan(200);
  expect(errors.filter((e) => /useRef|Invalid hook call|more than one copy of React/i.test(e))).toEqual([]);
});
