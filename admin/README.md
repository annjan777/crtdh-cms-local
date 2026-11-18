# CRTDH website editor (admin)

React 19 + Vite SPA for non-technical lab staff. It edits the public site page by page: pages and numbered
sections on the left, the real page on a canvas in the middle, the fields of the chosen section on the right,
and a draft bar on top (unpublished changes, Preview, Review & publish / Request review).

## Run

```bash
npm ci
VITE_USE_MOCK=1 npm run dev      # in-browser fake of the API, port 3200; users priya/ravi/sita/arjun/meera,
                                 # password local-test-pass, code 246810 (test values, src/mock/server.js)
npm run dev                      # against the API: /api proxied to localhost:8300
npm run build                    # dist/ (the mock is never bundled)
npm test                         # vitest: field renderer, validation, §4 error mapping, CSRF client, OAuth next
npm run e2e                      # Playwright against the mock (starts vite on 3200)
node scripts/tour.mjs [filter]   # screenshots of every screen at 1280/1024/390 (needs the mock dev server)
```

## How it fits together

- **API** (`src/api/`): contract §3 plus addendum A1–A13. Session cookie only; the CSRF token comes from the body
  of `GET /auth/csrf/` and login/MFA/password responses, is kept in memory and sent as `X-CSRFToken`
  (`CMS_CSRF_FAILED` → refetch and retry once). Every failure is an `ApiError` with a §4 `code`, `message`, `fix`.
- **Auth** (`src/auth/`): sign in → authenticator code, or first-time enrolment (QR, confirm, recovery codes
  shown once) → change a temporary password. `?next=` (OAuth) is followed only for same-origin paths.
- **Editor** (`src/editor/`): driven by the section registry from `GET /cms/pages/` (backend
  `apps/publishing/registry.py`). Autosave per record with the record `version`; a stale save shows who changed
  it and never overwrites. Text typed offline or after a session expiry is kept in localStorage and saved later.
- **Canvas** (`src/preview/`): `preview.html` renders the frontend lane's page components through the `@site`
  alias (`../frontend/src/site`, shim fallback in `src/preview/site-shim`).
- **Review / History / Users / Messages**: publish with live status, discard (one, or all from a Claude session),
  restore a version as unpublished changes, user admin (A12), contact-form messages (publisher/admin).

The old per-resource manager screens were removed; see `docs/cms-mapping.md` for where each one went.
