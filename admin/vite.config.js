import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const here = path.dirname(fileURLToPath(import.meta.url));

// The canvas renders the real public page components from the frontend lane
// (`frontend/src/site`, page components `({ data }) => JSX`) through `@site`.
// A production build must use them: if they are missing, `vite build` fails
// instead of silently shipping the shim (QA wave 2 D6). The shim is only for
// dev/tests without the frontend checkout, or when CRTDH_SITE_SHIM=1 is set
// explicitly for a dev server/test run (never honoured by `vite build`).
const siteDir = path.resolve(here, '../frontend/src/site');
const siteEntry = ['index.js', 'index.jsx', 'index.ts', 'index.tsx'].map((f) => path.join(siteDir, f)).find((f) => fs.existsSync(f));
const shimEntry = path.resolve(here, 'src/preview/site-shim/index.jsx');

// The site components import react from wherever they live; next to a
// frontend/node_modules that is a second React, and its hooks crash inside the
// admin's (useRef of null). dedupe resolves these from admin/node_modules.
const SHARED = ['react', 'react-dom', 'react-router'];

function sitePathFor(command) {
  if (command === 'build') {
    if (!siteEntry)
      throw new Error(`admin build: the public site components are missing (${siteDir}/index.js). ` +
        'Build with the repository root as context so frontend/src/site is included; the shim is never shipped.');
    return siteEntry;
  }
  return process.env.CRTDH_SITE_SHIM === '1' || !siteEntry ? shimEntry : siteEntry;
}

// In mock mode, seed images are served from the backend's media folder at the
// API media path previews use (/api/v1/media/<path>, session-only in prod).
const mediaRoot = path.resolve(here, '../backend/media');
function serveMedia() {
  return {
    name: 'crtdh-mock-media',
    configureServer(server) {
      server.middlewares.use('/api/v1/media', (req, res, next) => {
        const file = path.join(mediaRoot, decodeURIComponent(req.url.split('?')[0]));
        if (!file.startsWith(mediaRoot + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return next();
        const ext = path.extname(file).toLowerCase();
        const type = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.pdf': 'application/pdf' }[ext] || 'application/octet-stream';
        res.setHeader('Content-Type', type);
        res.setHeader('X-Content-Type-Options', 'nosniff');
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig(({ command }) => ({
  plugins: [react(), ...(process.env.VITE_USE_MOCK === '1' ? [serveMedia()] : [])],
  resolve: {
    alias: { '@site': sitePathFor(command) },
    dedupe: SHARED,
  },
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
  oxc: { jsx: { runtime: 'automatic' } },
  esbuild: { jsx: 'automatic' }, // vitest's bundled vite
  test: { environment: 'jsdom', include: ['src/**/*.test.{js,jsx}'] },
}));
