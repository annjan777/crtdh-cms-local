import { defineConfig, devices } from '@playwright/test';

// Runs e2e/built/*.spec.js against the production build (vite build + vite preview), in mock mode.
// The dev server pre-bundles dependencies and hides build-only problems such as a second React
// copy from frontend/node_modules (QA wave 2 D6).
export default defineConfig({
  testDir: './e2e/built',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:3201', ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 }, trace: 'retain-on-failure' },
  webServer: {
    command: 'npx vite build --outDir dist-e2e --emptyOutDir && npx vite preview --outDir dist-e2e --port 3201 --strictPort',
    env: { VITE_USE_MOCK: '1' },
    url: 'http://localhost:3201',
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
