import { expect } from '@playwright/test';

// Local test values from src/mock/server.js; never real credentials.
export const PASSWORD = 'local-test-pass';
export const CODE = '246810';

export async function signIn(page, username = 'priya', path = '/pages/home') {
  await page.goto(path);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Code', { exact: true }).fill(CODE);
  await page.getByRole('button', { name: 'Verify code' }).click();
  await expect(page.getByRole('link', { name: 'CRTDH website' })).toBeVisible();
}

export const canvas = (page) => page.frameLocator('iframe[title*="Select a section"]');
export const panel = (page) => page.locator('aside.field-panel');

export function mock(page, fn, ...args) {
  return page.evaluate(([f, a]) => window.__crtdhMock[f](...a), [fn, args]);
}
