// Download / upload backup (owner decision 2026-11-20): Admins only; upload restores as unpublished changes.
import { test, expect } from '@playwright/test';
import { signIn } from './helpers.js';

test('Admins get the Backup page with both downloads', async ({ page }) => {
  await signIn(page, 'sita', '/backup');
  await expect(page.getByRole('heading', { name: 'Backup', level: 1 })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download content', exact: true })).toHaveAttribute('href', /\/cms\/backup\/$/);
  await expect(page.getByRole('link', { name: 'Download content + photos' })).toHaveAttribute('href', /\/cms\/backup\/\?photos=1$/);
  await expect(page.getByRole('navigation', { name: 'Website' }).getByRole('link', { name: 'Backup' })).toBeVisible();
});

test('non-admins see no Backup link and no download buttons', async ({ page }) => {
  await signIn(page, 'priya', '/backup');
  await expect(page.getByRole('navigation', { name: 'Website' }).getByRole('link', { name: 'Backup' })).toHaveCount(0);
  await expect(page.getByText('Only an Admin can download or upload a backup.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download content', exact: true })).toHaveCount(0);
});

test('upload asks first, then restores as unpublished changes', async ({ page }) => {
  await signIn(page, 'sita', '/backup');
  await page.locator('#backup-file').setInputFiles({ name: 'crtdh-backup-2026-11-19-1000-content.zip', mimeType: 'application/zip', buffer: Buffer.from('PK') });
  const dialog = page.getByRole('dialog', { name: 'Restore this backup?' });
  await expect(dialog).toContainText('unpublished changes');
  await dialog.getByRole('button', { name: 'Restore as unpublished changes' }).click();
  await expect(page.getByText(/restored: 3 changes/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Review & publish' }).first()).toBeVisible();
});

test('a damaged backup is refused and says nothing changed', async ({ page }) => {
  await signIn(page, 'sita', '/backup');
  await page.locator('#backup-file').setInputFiles({ name: 'crtdh-backup-damaged.zip', mimeType: 'application/zip', buffer: Buffer.from('PK') });
  await page.getByRole('button', { name: 'Restore as unpublished changes' }).click();
  await expect(page.getByRole('alert')).toContainText('Nothing was changed');
  await expect(page.getByRole('alert')).toContainText('checksum does not match');
});

test('a file that is not a zip is refused before upload', async ({ page }) => {
  await signIn(page, 'sita', '/backup');
  await page.locator('#backup-file').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('x') });
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('alert')).toContainText('ends in .zip');
});
