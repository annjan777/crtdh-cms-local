import { expect, test } from '@playwright/test';
import { panel, signIn } from './helpers.js';

// A select filled from another list (Team member -> Group). The API pages its lists ({count, next, results});
// reading that as a bare array crashed the whole Team editor on staging (2026-11-20).
test('team member Group choices load from the paged list without crashing', async ({ page }) => {
  await signIn(page, 'priya', '/pages/team?section=team.members');
  await expect(page.getByText('Unexpected Application Error')).toHaveCount(0);
  const group = panel(page).getByRole('combobox', { name: /Group/ });
  await expect(group).toBeVisible();
  await expect.poll(() => group.locator('option').count()).toBeGreaterThan(1);
});
