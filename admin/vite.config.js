import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const here = path.dirname(fileURLToPath(import.meta.url));

// The canvas renders the real public page components from the frontend lane
// (`frontend/src/site`, page components `({ data }) => JSX`) through `@site`,
// in every mode (dev, tests, build). If they are missing, Vite stops with a
// clear error instead of silently using a stand-in (QA wave 2 D6/D7).
const siteDir = path.resolve(here, '../frontend/src/site');
const siteEntry = ['index.js', 'index.jsx', 'index.ts', 'index.tsx'].map((f) => path.join(siteDir, f)).find((f) => fs.existsSync(f));

// The site components import react from wherever they live; next to a
// frontend/node_modules that is a second React, and its hooks crash inside the
// admin's (useRef of null). dedupe resolves these from admin/node_modules.
// The site's own libraries (animation, icons, carousel) are installed here too, at the frontend's versions.
const SHARED = ['react', 'react-dom', 'react-router', 'framer-motion', 'lucide-react', 'embla-carousel-react'];

function sitePath() {
  if (!siteEntry)
    throw new Error(`admin: the public site components are missing (${siteDir}/index.js). ` +
      'Check out the whole repository (Docker: build with the repository root as context).');
  return siteEntry;
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

export default defineConfig(() => ({
  plugins: [react(), ...(process.env.VITE_USE_MOCK === '1' ? [serveMedia()] : [])],
  resolve: {
    // The canvas loads the public site's own stylesheet (src/preview/preview-entry.jsx). Its CSS imports
    // @fontsource packages, which the Docker build has only in admin/node_modules (frontend/ ships just
    // src/site), so resolve them from here. Same versions as frontend/package.json.
    alias: [
      { find: '@site-styles', replacement: path.join(siteDir, 'styles/index.css') },
      { find: '@site', replacement: sitePath() },
      { find: /^@fontsource\/(open-sans|montserrat)\//, replacement: path.join(here, 'node_modules/@fontsource/$1/') },
    ],
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
