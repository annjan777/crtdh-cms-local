import { reactRouter } from '@react-router/dev/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [reactRouter()],
  define: {
    // Contact relay endpoint (the only runtime request the public site makes).
    __CONTACT_API_URL__: JSON.stringify(process.env.CONTACT_API_URL || ''),
    __TURNSTILE_SITE_KEY__: JSON.stringify(process.env.TURNSTILE_SITE_KEY || ''),
  },
  server: { port: 3100, strictPort: true },
  preview: { port: 3100, strictPort: true },
  build: { assetsInlineLimit: 0 },
})
