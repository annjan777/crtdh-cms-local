import { expect, test } from '@playwright/test';
import { canvas, mock, signIn } from './helpers.js';

test('rich text with script is cleaned before it reaches the canvas', async ({ page }) => {
  let dialogs = 0;
  page.on('dialog', (d) => {
    dialogs += 1;
    d.dismiss();
  });
  await signIn(page, 'priya', '/pages/about');
  await mock(page, 'otherUserEdits', 'about-page', null, { intro: '<p>Safe <strong>bold</strong><img src=x onerror="window.top.__pwned=1"><script>window.top.__pwned=2</script></p>' });
  await page.reload();
  await expect(canvas(page).locator('strong', { hasText: 'bold' }).first()).toBeVisible();
  expect(await canvas(page).locator('img[onerror], script:not([type=module]):not([src])').count()).toBe(0);
  expect(await page.evaluate(() => window.__pwned)).toBeUndefined();
  expect(dialogs).toBe(0);
});

test('reset password and reset two-step sign-in each show a one-time temporary password', async ({ page }) => {
  await signIn(page, 'sita', '/users');
  await page.getByRole('row', { name: /Ravi Kumar/ }).getByRole('button', { name: /Reset password/ }).click();
  let dlg = page.getByRole('dialog', { name: 'Reset the password for Ravi Kumar?' });
  await expect(dlg.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await dlg.getByRole('button', { name: 'Reset password' }).click();
  let temp = page.getByRole('dialog', { name: 'Temporary password for Ravi Kumar' });
  await expect(temp).toContainText('tmp-Hn4c-Lz8q-Wb3t');
  await expect(temp).toContainText('old password no longer works');
  await temp.getByRole('button', { name: 'Done' }).click();
  await page.getByRole('row', { name: /Priya Sen/ }).getByRole('button', { name: /Reset two-step sign-in for Priya Sen/ }).click();
  dlg = page.getByRole('dialog', { name: 'Reset two-step sign-in for Priya Sen?' });
  await expect(dlg).toContainText('current password stop working');
  await dlg.getByRole('button', { name: 'Reset two-step sign-in' }).click();
  temp = page.getByRole('dialog', { name: 'Temporary password for Priya Sen' });
  await expect(temp).toContainText('Two-step sign-in was reset');
  await expect(temp).toContainText('tmp-Hn4c-Lz8q-Wb3t');
  await temp.getByRole('button', { name: 'Done' }).click();
  await expect(page.getByText('tmp-Hn4c-Lz8q-Wb3t')).toHaveCount(0);
  await expect(page.getByRole('row', { name: /Priya Sen/ })).toContainText('Not set up yet');
});

test('a publish waiting for the upload machine can be cancelled; the site is unchanged', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await mock(page, 'setAgentOffline', true);
  await page.getByRole('button', { name: 'Publish 2 changes' }).click();
  await expect(page.getByText(/Waiting for upload machine/)).toBeVisible({ timeout: 15_000 });
  await page.getByRole('button', { name: 'Cancel publish' }).click();
  await expect(page.getByText('Publish cancelled.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Publish 2 changes' })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('crtdh-active-publish'))).toBeNull();
});

test('an unknown publish id (UUID) stops polling instead of retrying forever', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await page.evaluate(() => sessionStorage.setItem('crtdh-active-publish', '3f2b8c1e-0000-4000-8000-000000000000'));
  await page.reload();
  await expect(page.getByText('The publish status can’t be read right now.')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('crtdh-active-publish'))).toBeNull();
  await expect(page.getByRole('button', { name: 'Publish 2 changes' })).toBeVisible();
});

test('signing out removes that person’s kept drafts', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.objective');
  await mock(page, 'setOffline', true);
  await page.locator('aside.field-panel').getByLabel('Statement').fill('Draft for Priya only');
  await expect.poll(() => page.evaluate(() => localStorage.getItem('crtdh-draft:1:home-page:1'))).toContain('Draft for Priya');
  await page.getByRole('button', { name: 'Priya Sen' }).click();
  await page.getByRole('menuitem', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith('crtdh-draft:')))).toEqual([]);
});

test('a photo saved right after typing waits for the text autosave (no false conflict)', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  const panel = page.locator('aside.field-panel');
  await page.evaluate(() => (window.__crtdhMockLatency = 700));
  await panel.getByRole('textbox', { name: 'Headline', exact: true }).fill('Typed just before the photo');
  await panel.locator('input[type=file]').first().setInputFiles(new URL('./fixtures/photo-2400.jpg', import.meta.url).pathname);
  await panel.getByRole('button', { name: 'Save photo' }).click();
  await expect(panel.getByText('Saved · not live yet')).toBeVisible({ timeout: 15_000 });
  await expect(panel.getByRole('alert').filter({ hasText: 'changed this' })).toHaveCount(0);
  const row = (await mock(page, 'state')).rows['hero-slides']['18'];
  expect(row.heading).toBe('Typed just before the photo');
  expect(row.image).toMatch(/^data:image/);
});
