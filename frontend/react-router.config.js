import { PAGE_PATHS } from './src/site/registry.js'

// Static site: every public route is prerendered at build time from the
// published snapshot (contracts §5). No server runtime; ssr is off.
export default {
  appDirectory: 'app',
  ssr: false,
  // '/404' renders the catch-all route; scripts/postbuild.mjs copies it to 404.html.
  prerender: [...PAGE_PATHS, '/404'],
}
