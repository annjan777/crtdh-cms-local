import { expect, test } from '@playwright/test';
import { signIn } from './helpers.js';

// Docs promise "CMS → Claude access → Disconnect Claude" (docs/connect-claude.md, docs/mcp.md).
test('an editor sees and disconnects their own Claude connection after a named confirmation', async ({ page }) => {
  await signIn(page, 'ravi', '/claude-access');
  await expect(page.getByRole('heading', { level: 1, name: 'Claude access' })).toBeVisible();
  await expect(page.getByText(/Claude · connected/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Everyone’s connections' })).toHaveCount(0); // not an Admin
  await page.getByRole('button', { name: 'Disconnect Claude' }).click();
  const dialog = page.getByRole('dialog', { name: 'Disconnect Claude from your account?' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText(/Claude · connected/)).toBeVisible();
  await page.getByRole('button', { name: 'Disconnect Claude' }).click();
  await dialog.getByRole('button', { name: 'Disconnect Claude' }).click();
  await expect(page.getByText('Claude is disconnected from your account.')).toBeVisible();
  await expect(page.getByText('Claude isn’t connected to your account.')).toBeVisible();
});

test('an admin disconnects someone else’s Claude by name', async ({ page }) => {
  await signIn(page, 'sita', '/pages/home');
  await page.getByRole('button', { name: /Sita/ }).click();
  await page.getByRole('menuitem', { name: 'Claude access' }).click();
  await expect(page).toHaveURL(/\/claude-access$/);
  const row = page.getByRole('row', { name: /Priya Sen/ });
  await row.getByRole('button', { name: 'Disconnect Claude for Priya Sen' }).click();
  const dialog = page.getByRole('dialog', { name: 'Disconnect Claude for Priya Sen?' });
  await dialog.getByRole('button', { name: 'Disconnect Priya Sen' }).click();
  await expect(page.getByText('Claude is disconnected for Priya Sen.')).toBeVisible();
  await expect(page.getByRole('row', { name: /Priya Sen/ })).toHaveCount(0);
  await expect(page.getByRole('row', { name: /Ravi Kumar/ })).toBeVisible();
});
