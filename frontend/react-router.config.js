import { PAGE_PATHS } from './src/site/registry.js'

// Static site: every public route is prerendered at build time from the
// published snapshot (contracts §5). No server runtime; ssr is off.
export default {
  appDirectory: 'app',
  ssr: false,
  // Public URLs end in "/" (registry paths, links, canonical, sitemap). React Router keys prerendering on the
  // path without it and writes <page>/index.html either way; the routes match "/about/" and "/about" alike, and
  // a client navigation to "/about/" loads /about.data, which is what the prerender writes.
  // '/404' renders the catch-all route; scripts/postbuild.mjs copies it to 404.html.
  prerender: [...PAGE_PATHS.map((p) => (p === '/' ? p : p.replace(/\/$/, ''))), '/404'],
}
