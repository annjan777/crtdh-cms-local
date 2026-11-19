import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { canvas, signIn } from '../helpers.js';

// QA wave 2 D3: the production gateway's CSP / X-Frame-Options blocked the same-origin canvas iframe.
// vite preview sends no security headers, so add exactly the ones deploy/nginx/templates/gateway.conf.template
// gives the SPA (location /) and /preview.html (location = /preview.html) to each document response.
const here = path.dirname(fileURLToPath(import.meta.url));
const conf = fs.readFileSync(path.resolve(here, '../../../deploy/nginx/templates/gateway.conf.template'), 'utf8');
const cms = conf.slice(conf.indexOf('server_name ${CMS_HOST};'), conf.indexOf('server_name ${CONTACT_HOST};'));
const vars = Object.fromEntries([...cms.matchAll(/set \$(\w+) "([^"]*)";/g)].map((m) => [m[1], m[2]]));

function headersFor(location) {
  const start = cms.indexOf(`location ${location} {`);
  const block = cms.slice(start, cms.indexOf('\n    }', start));
  const out = {};
  for (const m of block.matchAll(/add_header ([\w-]+) (\$\w+|"[^"]*") always;/g))
    out[m[1]] = m[2].startsWith('$') ? vars[m[2].slice(1)] : m[2].slice(1, -1);
  delete out['Strict-Transport-Security']; // http://localhost
  return out;
}

const frontendModules = fs.existsSync(path.resolve(here, '../../../frontend/node_modules/react'));

test('canvas renders under the production gateway headers', async ({ page }) => {
  test.skip(!frontendModules, 'needs frontend/node_modules (same setup as canvas-build.spec.js)');
  const violations = [];
  page.on('console', (m) => /Content Security Policy|frame-src|frame-ancestors|X-Frame-Options/i.test(m.text()) && violations.push(m.text()));
  await page.route('**/*', async (route) => {
    const req = route.request();
    if (req.resourceType() !== 'document') return route.continue();
    const resp = await route.fetch();
    const loc = new URL(req.url()).pathname === '/preview.html' ? '= /preview.html' : '/';
    await route.fulfill({ response: resp, headers: { ...resp.headers(), ...headersFor(loc) } });
  });
  await signIn(page, 'priya', '/pages/home');
  await expect(canvas(page).locator('.site-header')).toBeVisible();
  const hero = canvas(page).locator('[data-cms-section="home.hero"]').first();
  await expect(hero).toBeVisible();
  await expect(hero).toHaveCSS('cursor', 'pointer'); // the canvas's editor stylesheet applied under style-src 'self'
  expect(violations).toEqual([]);
});
