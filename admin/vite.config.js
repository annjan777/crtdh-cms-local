import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const here = path.dirname(fileURLToPath(import.meta.url));

// The canvas renders the real public page components from the frontend lane
// (`frontend/src/site`, page components `({ data }) => JSX`). Until that
// package exists, `@site` points at a local shim so this lane builds.
const siteDir = path.resolve(here, '../frontend/src/site');
const siteEntry = ['index.js', 'index.jsx', 'index.ts', 'index.tsx'].map((f) => path.join(siteDir, f)).find((f) => fs.existsSync(f));
const sitePath = process.env.CRTDH_SITE_SHIM === '1' || !siteEntry ? path.resolve(here, 'src/preview/site-shim/index.jsx') : siteEntry;

// In mock mode, seed images are served from the backend's media folder.
const mediaRoot = path.resolve(here, '../backend/media');
function serveMedia() {
  return {
    name: 'crtdh-mock-media',
    configureServer(server) {
      server.middlewares.use('/media', (req, res, next) => {
        const file = path.join(mediaRoot, decodeURIComponent(req.url.split('?')[0]));
        if (!file.startsWith(mediaRoot) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return next();
        const ext = path.extname(file).toLowerCase();
        const type = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.pdf': 'application/pdf' }[ext] || 'application/octet-stream';
        res.setHeader('Content-Type', type);
        res.setHeader('X-Content-Type-Options', 'nosniff');
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveMedia()],
  resolve: { alias: { '@site': sitePath } },
  build: {
    rollupOptions: {
      input: { main: path.resolve(here, 'index.html'), preview: path.resolve(here, 'preview.html') },
    },
  },
  server: {
    port: 3200,
    strictPort: true,
    proxy: process.env.VITE_USE_MOCK === '1' ? undefined : { '/api': 'http://localhost:8300' },
  },
  preview: { port: 3200, strictPort: true },
});
