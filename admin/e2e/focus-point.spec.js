import { expect, test } from '@playwright/test';
import { canvas, panel, signIn } from './helpers.js';

// Hero photos: the editor clicks the part of the photo to keep in view. The phone and computer previews and
// the real page on the canvas all crop around that point, and it autosaves like any other field.
test('clicking the hero photo sets its focus point, shown in previews and on the page', async ({ page }) => {
  await signIn(page, 'priya', '/pages/home?section=home.hero');
  const picker = panel(page).locator('.focus-picker').first();
  await expect(picker).toBeVisible();
  await expect(picker.getByText('Part of the photo to keep in view')).toBeVisible();

  const photo = picker.locator('.focus-picker__photo');
  const box = await photo.boundingBox();
  await page.mouse.click(box.x + box.width * 0.2, box.y + box.height * 0.3);

  await expect(picker.locator('.focus-picker__dot')).toHaveAttribute('style', /left: 20%; top: 30%/);
  await expect(picker.locator('.focus-preview--phone img')).toHaveAttribute('style', /object-position: 20% 30%/);
  await expect(panel(page).getByText('Saved · not live yet')).toBeVisible();
  await expect(canvas(page).locator('[data-cms-section="home.hero"] .hero__slide img').first())
    .toHaveAttribute('style', /object-position: 20% 30%/);

  // Keyboard: arrow keys move the point (2% a press, 10% with Shift).
  await picker.locator('.focus-picker__dot').focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Shift+ArrowDown');
  await expect(picker.locator('.focus-picker__dot')).toHaveAttribute('style', /left: 22%; top: 40%/);
});
