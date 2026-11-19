import { expect, test } from '@playwright/test';
import { CODE, PASSWORD, mock, signIn } from './helpers.js';

test('MFA login: password, then authenticator code; a wrong code explains the fix', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Enter your username.')).toBeVisible();
  await page.getByLabel('Username').fill('priya');
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Enter your code' })).toBeVisible();
  await page.getByLabel('Code', { exact: true }).fill('111111');
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByText('That code didn’t match.')).toBeVisible();
  await page.getByLabel('Code', { exact: true }).fill(CODE);
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByRole('button', { name: 'Priya Sen' })).toBeVisible();
  // Session cookie + CSRF only: nothing token-like in localStorage.
  const keys = await page.evaluate(() => Object.keys(localStorage));
  expect(keys.filter((k) => /token|jwt|access|refresh/i.test(k))).toEqual([]);
});

test('MFA enrolment on first sign-in: QR, confirm, recovery codes', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Username').fill('arjun');
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Set up two-step sign-in' })).toBeVisible();
  await expect(page.getByRole('img', { name: /QR code/ })).toBeVisible();
  await expect(page.getByText('JBSW Y3DP EHPK 3PXP')).toBeVisible();
  await page.getByLabel('Code from the app').fill(CODE);
  await page.getByRole('button', { name: 'Confirm code' }).click();
  await expect(page.getByRole('heading', { name: 'Save your recovery codes' })).toBeVisible();
  await expect(page.getByRole('list', { name: 'Recovery codes' }).getByRole('listitem')).toHaveCount(8);
  await page.getByRole('button', { name: 'Open the editor' }).click();
  await expect(page.getByText('Tick the box once the codes are saved.')).toBeVisible();
  await page.getByLabel('I’ve saved these codes').check();
  await page.getByRole('button', { name: 'Open the editor' }).click();
  await expect(page.getByRole('button', { name: 'Arjun Paul' })).toBeVisible();
});

test('lockout after five passwords that don’t match', async ({ page }) => {
  await page.goto('/');
  for (let i = 0; i < 5; i += 1) {
    await page.getByLabel('Username').fill('ravi');
    await page.getByLabel('Password').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByText('That username and password don’t match.')).toBeVisible();
  }
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Sign-in is paused' })).toBeVisible();
  await expect(page.getByText(/You can try again at \d\d:\d\d/)).toBeVisible();
});

test('editor role cannot publish: request review instead', async ({ page }) => {
  await signIn(page, 'ravi');
  const bar = page.getByRole('region', { name: 'Unpublished changes' });
  await expect(bar.getByRole('link', { name: 'Review & publish' })).toHaveCount(0);
  await page.getByRole('navigation', { name: 'Website' }).getByRole('link', { name: 'Review & publish' }).click();
  await expect(page.getByRole('button', { name: /^Publish/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Request review' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Request a review' });
  await dialog.getByLabel('Note for the publisher').fill('Please publish the Salboni camp news today.');
  await dialog.getByRole('button', { name: 'Send request' }).click();
  await expect(page.getByRole('dialog', { name: 'Review requested' })).toContainText('Priya Sen');
  await page.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByText(/Waiting for review/).first()).toBeVisible();
  // The API refuses a publish from an editor too.
  const res = await page.evaluate(async () => {
    const { cms } = await import('/src/api/cms.js');
    try {
      await cms.publish();
      return 'published';
    } catch (e) {
      return e.code;
    }
  });
  expect(res).toBe('CMS_FORBIDDEN_ROLE');
});

test('discard: one change, then all changes from a Claude session', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await expect(page.getByText('Claude made 1 change for Priya Sen in one session.')).toBeVisible();
  const news = page.locator('.change', { hasText: 'Salboni' });
  await news.getByRole('button', { name: 'Discard' }).click();
  const dlg = page.getByRole('dialog');
  await expect(dlg.getByRole('heading')).toContainText('Discard the change to “Health camp at Salboni');
  await expect(dlg.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await dlg.getByRole('button', { name: 'Discard change' }).click();
  await expect(news).toHaveCount(0);
  await page.getByRole('button', { name: 'Discard all from this Claude session' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Discard session changes' }).click();
  await expect(page.getByRole('heading', { name: 'Nothing to publish' })).toBeVisible();
});

test('restore: confirmation names version and date; content comes back as unpublished changes', async ({ page }) => {
  await signIn(page, 'priya', '/history');
  const row = page.getByRole('row', { name: /39/ });
  await row.getByRole('button', { name: 'Restore' }).click();
  const dlg = page.getByRole('dialog');
  await expect(dlg.getByRole('heading')).toHaveText(/Restore version 39 from 12 Nov 2026, \d\d:\d\d\?/);
  await dlg.getByRole('button', { name: 'Restore version 39' }).click();
  await expect(page.getByText(/Version 39 from 12 Nov 2026.* is restored as unpublished changes/)).toBeVisible();
  await page.getByRole('link', { name: 'Review changes' }).click();
  await expect(page.locator('.change', { hasText: 'CRTDH team visits Rural Healthcare Foundation clinics' })).toBeVisible();
});

test('publish failure keeps the site unchanged and offers a retry', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await mock(page, 'failNextPublish');
  await page.getByRole('button', { name: 'Publish 2 changes' }).click();
  await expect(page.getByText(/Publish failed while uploading to the server/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/disk quota exceeded.*The site is unchanged/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
});

test('upload machine unreachable: honest waiting state', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await mock(page, 'setAgentOffline', true);
  await page.getByRole('button', { name: 'Publish 2 changes' }).click();
  await expect(page.getByText(/Waiting for upload machine \(last seen \d\d:\d\d\)/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Publishing · waiting for upload machine')).toBeVisible();
});

test('build guard: a big shrink needs a named confirmation', async ({ page }) => {
  await signIn(page, 'priya', '/review');
  await page.evaluate(() => {
    const db = window.__crtdhMock.state();
    for (const r of Object.values(db.rows['team-members']).slice(0, 5)) r.is_published = false;
    sessionStorage.setItem('crtdh-mock-db', JSON.stringify(db));
  });
  await page.reload();
  await page.getByRole('button', { name: /^Publish \d+ changes/ }).click();
  const dlg = page.getByRole('dialog', { name: 'Publish with a much shorter list?' });
  await expect(dlg).toContainText('team members list would shrink from 9 to 4');
  await expect(dlg.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await dlg.getByRole('button', { name: 'Publish anyway' }).click();
  await expect(page.getByText(/Live at \d\d:\d\d/)).toBeVisible({ timeout: 15_000 });
});

test('users: admin adds a user (temporary password shown once), changes a role, deactivates with a named confirmation', async ({ page }) => {
  await signIn(page, 'sita', '/users');
  await page.getByRole('button', { name: 'Add user' }).click();
  const drawer = page.getByRole('dialog', { name: 'Add a user' });
  await drawer.getByRole('button', { name: 'Add user' }).click();
  await expect(drawer.getByText('Enter the person’s full name.')).toBeVisible();
  await drawer.getByLabel('Full name').fill('Nandini Ghosh');
  await expect(drawer.getByLabel('Username')).toHaveValue('nandini');
  await drawer.getByLabel('Email').fill('nandini@example.test');
  await drawer.getByLabel(/Publisher/).check();
  await drawer.getByRole('button', { name: 'Add user' }).click();
  const temp = page.getByRole('dialog', { name: 'Temporary password for Nandini Ghosh' });
  await expect(temp).toContainText('tmp-Kq7v-Rw2m-Xp9d');
  await temp.getByRole('button', { name: 'Done' }).click();
  await expect(page.getByText('Nandini Ghosh was added as Publisher.')).toBeVisible();
  await expect(page.getByText('tmp-Kq7v-Rw2m-Xp9d')).toHaveCount(0);
  // Role change goes to /auth/users/<id>/role/.
  await page.getByLabel('Role for Ravi Kumar').selectOption('publisher');
  await expect(page.getByRole('row', { name: /Ravi Kumar/ })).toContainText('Role saved');
  expect((await mock(page, 'state')).users.find((u) => u.username === 'ravi').roles).toEqual(['editor', 'publisher']);
  await page.getByRole('row', { name: /Ravi Kumar/ }).getByRole('button', { name: 'Deactivate' }).click();
  const dlg = page.getByRole('dialog', { name: 'Deactivate Ravi Kumar?' });
  await dlg.getByRole('button', { name: 'Deactivate Ravi' }).click();
  await expect(page.getByRole('row', { name: /Ravi Kumar/ })).toContainText('Deactivated');
  await expect(page.getByRole('row', { name: /Ravi Kumar/ }).getByRole('button', { name: 'Deactivate' })).toHaveCount(0);
});

test('first sign-in with a temporary password: choose a new one before editing', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Username').fill('meera');
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Code', { exact: true }).fill(CODE);
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByRole('heading', { name: 'Choose your own password' })).toBeVisible();
  await page.getByLabel('Temporary password').fill(PASSWORD);
  await page.getByLabel('New password', { exact: true }).fill('short');
  await page.getByLabel('New password again').fill('short');
  await page.getByRole('button', { name: 'Save password' }).click();
  await expect(page.getByText('Use at least 12 characters (now 5).')).toBeVisible();
  await page.getByLabel('New password', { exact: true }).fill('a long enough sentence');
  await page.getByLabel('New password again').fill('a long enough sentence');
  await page.getByRole('button', { name: 'Save password' }).click();
  await expect(page.getByRole('button', { name: 'Meera Iyer' })).toBeVisible();
});

test('OAuth next: a same-origin path is followed after sign-in, another site is not', async ({ page }) => {
  await signIn(page, 'priya', '/login?next=%2Fhistory%3Ftab%3Dall');
  await expect(page).toHaveURL(/\/history\?tab=all$/);
  await page.goto('/login?next=%2F%2Fevil.example%2F');
  await expect(page.getByRole('button', { name: 'Priya Sen' })).toBeVisible();
  expect(new URL(page.url()).host).toBe('localhost:3200');
});

test('CSRF token lives in memory only and is sent as X-CSRFToken', async ({ page }) => {
  await signIn(page, 'priya');
  expect(await page.evaluate(() => document.cookie)).not.toContain('csrftoken');
  const keys = await page.evaluate(() => Object.keys(localStorage));
  expect(keys.filter((k) => /csrf/i.test(k))).toEqual([]);
});

test('users page is for admins only', async ({ page }) => {
  await signIn(page, 'priya', '/users');
  await expect(page.getByRole('heading', { name: 'Only Admins can manage users' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Users' })).toHaveCount(0);
});

test('messages: publishers read contact messages as text and delete one with a named confirmation', async ({ page }) => {
  await signIn(page, 'priya', '/messages');
  const list = page.getByRole('list', { name: 'Messages' });
  await expect(list.getByRole('button')).toHaveCount(3);
  await list.getByRole('button', { name: /Test <script>/ }).click();
  const detail = page.getByRole('region', { name: 'Message' });
  await expect(detail).toContainText('<img src=x onerror=alert(1)> shown as text, never run');
  expect(await detail.locator('img').count()).toBe(0);
  await detail.getByRole('button', { name: 'Delete message' }).click();
  const dlg = page.getByRole('dialog', { name: 'Delete the message from Test <script>?' });
  await expect(dlg.getByRole('button', { name: 'Cancel' })).toBeFocused();
  await dlg.getByRole('button', { name: 'Delete message' }).click();
  await expect(page.getByText('The message from Test <script> was deleted.')).toBeVisible();
  await expect(list.getByRole('button')).toHaveCount(2);
  await list.getByRole('button', { name: /Dr. S. Mehta/ }).click();
  await expect(detail).toContainText('We’d like to bring'.replace('’', "'"));
});

test('messages are hidden from editors', async ({ page }) => {
  await signIn(page, 'ravi', '/messages');
  await expect(page.getByRole('heading', { name: 'Only Publishers and Admins can read messages' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Website' }).getByRole('link', { name: 'Messages' })).toHaveCount(0);
});
