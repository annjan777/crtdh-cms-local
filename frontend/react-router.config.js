import path from 'node:path'
import { PAGE_PATHS } from './src/site/registry.js'

// The publish worker (backend run_frontend_build) sets BUILD_OUTPUT_DIR to where it reads the static site, which
// React Router writes to <buildDirectory>/client. In production the worker's frontend/ is read-only, so that is
// outside this folder (deploy/worker/Dockerfile). Unset = build/ here, as before.
const clientDir = process.env.BUILD_OUTPUT_DIR ? path.resolve(process.env.BUILD_OUTPUT_DIR) : null
if (clientDir && path.basename(clientDir) !== 'client') throw new Error(`BUILD_OUTPUT_DIR must end in /client (got ${clientDir})`)

// Static site: every public route is prerendered at build time from the
// published snapshot (contracts §5). No server runtime; ssr is off.
export default {
  appDirectory: 'app',
  buildDirectory: clientDir ? path.dirname(clientDir) : 'build',
  ssr: false,
  // Public URLs end in "/" (registry paths, links, canonical, sitemap). React Router keys prerendering on the
  // path without it and writes <page>/index.html either way; the routes match "/about/" and "/about" alike, and
  // a client navigation to "/about/" loads /about.data, which is what the prerender writes.
  // '/404' renders the catch-all route; scripts/postbuild.mjs copies it to 404.html.
  prerender: [...PAGE_PATHS.map((p) => (p === '/' ? p : p.replace(/\/$/, ''))), '/404'],
}
