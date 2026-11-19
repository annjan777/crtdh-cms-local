import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testIgnore: ['built/**'], // production-build checks: playwright.build.config.js
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  workers: 4,
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
