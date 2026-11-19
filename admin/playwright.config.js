import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testIgnore: ['built/**'], // production-build checks: playwright.build.config.js
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  // 4 workers starve the single Vite dev server on small CI machines: storyboard and collections then time
  // out waiting for autosave/preview (they pass alone and at 2 workers). Override with --workers.
  workers: 2,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:3200', ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 }, trace: 'retain-on-failure' },
  webServer: {
    command: 'npx vite --port 3200',
    env: { VITE_USE_MOCK: '1' },
    url: 'http://localhost:3200',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
