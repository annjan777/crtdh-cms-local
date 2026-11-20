import { expect, test } from '@playwright/test';
import { signIn } from './helpers.js';

// The window itself must never scroll: each column (page list, canvas, edit panel) scrolls on its own.
// Before the fix, switch and file inputs in the edit panel escaped the shell's clip, the window grew about
// 1000px taller than the screen, and the mouse wheel slid the whole editor up instead of scrolling the panel.
test.use({ viewport: { width: 1280, height: 640 } });

for (const path of ['/pages/home', '/pages/team', '/review', '/messages', '/backup']) {
  test(`window never scrolls; every column reaches its end: ${path}`, async ({ page }) => {
    await signIn(page, 'priya', path);
    await page.waitForTimeout(800);
    const boxes = await page.evaluate(() =>
      [...document.querySelectorAll('.col-nav, .canvas-scroll, .field-panel, .page-main')]
        .filter((e) => e.scrollHeight > e.clientHeight + 2)
        .map((e, i) => {
          e.dataset.sb = String(i);
          const r = e.getBoundingClientRect();
          return { i, x: r.left + r.width / 2, y: r.top + Math.min(r.height / 2, 120) };
        }),
    );
    for (const { i, x, y } of boxes) {
      await page.mouse.move(x, y);
      for (let n = 0; n < 40; n += 1) await page.mouse.wheel(0, 400);
      await expect
        .poll(() => page.evaluate((k) => {
          const e = document.querySelector(`[data-sb="${k}"]`);
          return e.scrollTop + e.clientHeight >= e.scrollHeight - 2;
        }, i))
        .toBe(true);
    }
    const [docHeight, viewHeight, scrollY] = await page.evaluate(() => [
      document.documentElement.scrollHeight,
      window.innerHeight,
      window.scrollY,
    ]);
    expect(docHeight).toBeLessThanOrEqual(viewHeight + 1);
    expect(scrollY).toBe(0);
  });
}
