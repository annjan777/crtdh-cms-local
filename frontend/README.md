# CRTDH public website (static build)

The public site for CRTDH, IIT Kharagpur. It is a **static site**: React Router 7 (framework mode, `ssr: false`)
prerenders every public page at build time from one published **snapshot** (`docs/contracts/v3-contracts.md` §1,
§5). The output is plain files that the campus publish agent uploads to the CIC host. The site makes no API calls
at run time; the only request it sends is the contact form's POST to `CONTACT_API_URL`.

## How it is built in production

The CMS publish worker (`backend/apps/publishing/publish.py`, image `deploy/worker/Dockerfile`) runs the build for
each publish with:

| Variable | Set by | Meaning |
|---|---|---|
| `SNAPSHOT_PATH` | worker | this publish's `snapshot.json` (`app/snapshot.server.js` reads it; the snapshot guard refuses a missing or incomplete one) |
| `BUILD_OUTPUT_DIR` | worker | where the static site is written; must end in `/client` (`react-router.config.js` builds into its parent) |
| `SITE_URL`, `CONTACT_API_URL`, `TURNSTILE_SITE_KEY` | `deploy/.env` | canonical URLs and sitemap, contact form endpoint and Turnstile widget |

Without `BUILD_OUTPUT_DIR` the output is `build/client/`. `scripts/postbuild.mjs` then writes `404.html`,
`sitemap.xml`, `robots.txt`, the CSP script hashes and `.htaccess`.

## Local development

```bash
npm ci
npm run snapshot:dev        # snapshot.json from the team stub, with real image sizes
npm run dev                 # http://localhost:3100
npm run build && MEDIA_ROOT=../backend/seed_media npm run serve   # static preview of build/client, like the CIC host
```

There is no frontend container: the site is only ever built by the worker (or the commands above) and served by
the CIC host. The admin's page editor renders the same components from `src/site` in its canvas.

## Checks

```bash
npm test                    # unit (vitest): build output, hardening
npm run test:e2e            # Playwright against the built site (static, parity, contact)
npm run size                # JS budget per page
npm run sweep               # placeholders, empty headings, missing alt, broken internal links in build/client
npm run check:apache        # .htaccess under Apache with AllowOverride FileInfo (needs apache2)
```

## Layout

```
app/                     React Router app: root.jsx, routes.js, routes/<page>.jsx (loaders read the snapshot),
                         snapshot.server.js (build-time only), seo.js
src/site/                the page components shared with the admin canvas (`@site`): pages/, components/,
                         registry.js (page paths and which snapshot data each page needs), styles/, fonts/
scripts/                 postbuild, dev-snapshot, serve, size, sweep, apache-check
tests/unit, tests/e2e
react-router.config.js   prerender list from src/site/registry.js; buildDirectory from BUILD_OUTPUT_DIR
```
