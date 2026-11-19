import { defineConfig } from '@playwright/test'

// E2E against the built static site (npm run build first; see tests/e2e/README in DESIGN.md).
// Uses the system Chrome; no browser download needed.
export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 60_000,
  fullyParallel: true,
  workers: 4,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3100',
    launchOptions: { executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome' },
  },
  webServer: {
    command: 'node scripts/serve.mjs',
    url: 'http://localhost:3100/',
    reuseExistingServer: true,
    env: { PORT: '3100' },
  },
})
