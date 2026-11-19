# Code changes: `v3/remediation` (base `1f29d21`, the audited release candidate)

18 commits (one of them a revert), no database migrations. Not pushed, not deployed. Every behaviour change has a test that
fails on the old code (checked for R-1, R-7, F-07) or pins the new behaviour.

## R-7 / F-07: false "Leave before your change is saved?" (f5acd2c)
- `admin/src/editor/EditorContext.jsx`: on load, a draft kept in the browser whose values equal the CMS's is
  deleted silently. Restored drafts are tracked, and `discardRestored()` drops them (conflicts reload from the CMS).
- `admin/src/editor/EditorPage.jsx`: the restored-changes banner says when a change can't save (invalid or
  conflict) and offers **Discard**; it no longer claims "being saved now" for a change that can't save.
- `admin/e2e/unsaved-guard.spec.js` (new, 4 tests).
- **Root cause (reproduced):** a change left with "Leave anyway" while unsaveable (e.g. a required field emptied)
  stayed in localStorage and was restored on every later visit, so the page warned although nothing had been
  changed in that visit.
- Security: none. Drafts stay per-user (unchanged).

## R-5 / F-05: privacy notice on the published site (385f217)
- `deploy/worker/Dockerfile`, `deploy/worker/Dockerfile.dockerignore`: the worker image copies
  `docs/privacy-notice.md` and sets `PRIVACY_NOTICE_PATH`.
- `frontend/src/site/components/Layout.jsx`: footer bottom strip "How we use contact messages" (→ `#privacy`, or
  to the short notice if the full one is absent) and "Last updated <publish date>"; year from the snapshot.
- `backend/tests/security/test_repo_hygiene.py`: pins the dockerignore exception and the COPY.
- **Root cause:** `.dockerignore` admitted only `backend/` and `frontend/`, so the build never had the notice. The
  old-design restore (429bd2d) had also dropped the footer link. The audit's "CMS content is empty" was wrong.
- The grievance-contact sentence still has a placeholder; the build leaves placeholder sentences out (owner input).

## Footer and text alignment (87a695c, 2356230): owner feedback 2026-11-20
- `Layout.jsx`/`Layout.css`: footer in the header's sky blue (#e0f2fe, bottom strip #cde8fb), the logo and wordmark
  as in the header (the wordmark was dark on dark, so invisible), left-aligned copy. All text pairs ≥ 4.5:1.
- `styles/global.css`: justification only for unclassed body paragraphs in `<main>` and rich text, from 768 px,
  with hyphenation. Short UI text (addresses, subtitles, captions, notes) is ragged-right.

## R-8 / F-06: click-to-load map and video (930dcee)
- `frontend/src/site/components/ClickToLoad.{jsx,css}` (new): `YouTubeFacade`, `MapFacade`, `directionsUrl`.
- Used by `VideoBlock.jsx`, `pages/Innovations.jsx`, `pages/Home.jsx`, `pages/Contact.jsx` (CSS sizing so the
  box does not move when the embed loads).
- Home **Get Directions** opened the map *embed* URL; it now opens a Google Maps search for the address.
- `docs/privacy-notice.md`: "Maps and videos" paragraph.
- `frontend/tests/e2e/embeds.spec.js` (new, 14 tests): no Google or YouTube request on load on all 12 pages; map
  and video load only after the click; no layout jump.
- Restores behaviour that the old-design port (429bd2d) had dropped. Security/privacy: no third-party request
  before consent by click.

## F-17 (new): admin browser tests out of date (517c784)
- `admin/e2e/editor.spec.js`, `review-fixes.spec.js`, `canvas-real-site.spec.js`: 6 tests updated to the shipped
  UI (photo field without a description box or focus picker, restored Team heading, the cross-page section on
  Social impact). Assertions keep their strength: e.g. "a photo is never saved without a description" now checks
  the automatic description is stored.
- `admin/playwright.config.js`: 2 workers (4 starved the dev server; 2 timing tests failed only under load).

## R-1 / F-01: MFA switch-over (05e20b8)
- `backend/apps/accounts/mfa.py`: the session records the sign-in method (`totp` | `password`);
  `session_signed_in()` is the single rule. With `MFA_ENABLED`, only `totp` sessions count.
- `authentication.py` and `views.py` use it; the MFA-off login records `password`.
- Tests: `apps/accounts/tests/test_mfa_disabled.py` (+3), `tests/claude_mcp/test_oauth.py` helpers record `totp`.
- **Gap closed:** before this, a session signed in with only a password while MFA was off kept working for up to 8 h
  after MFA was switched on, and could authorise Claude.
- Verified unchanged (existing tests): TOTP enrolment, replay refusal, single-use recovery codes, pending-step
  expiry, lockout, OAuth authorize needs an MFA session.

## R-9 / F-09: test seeds (a64961f)
- `tests/e2e/test_00_harness.py`: the stack's repr (printed in tracebacks) carries no TOTP seed or password.
- `backend/tests/infra/test_seed_test_users.py`: production compose and env template never set
  `CRTDH_ALLOW_TEST_SEED`; cms runs `CRTDH_ENV=production`. Existing refusals unchanged. No history rewrite.

## R-17 / F-14, F-15 (7893674)
- `deploy/nginx/templates/gateway.conf.template`: CMS host `location ~ /\.(?!well-known/) { return 404; }`.
- `backend/apps/publishing/agent.py` and `publish_agent/cmsclient.py`: HMAC over `get_full_path()` (path + query)
  on both sides. Identical for today's requests (no query strings), so old and new agent versions both work.
- Tests: gateway rule; query appended or changed → 401; agent signs the same string; the agent's fake CMS verifies
  the full path.

## R-11 / F-11: containers (e84189a)
- `deploy/staging/agent/Dockerfile`: `USER 65534:65534` default (compose still sets the host user).
- `deploy/staging/sftp/Dockerfile`: comment documenting why sshd stays root.
- `.github/workflows/ci.yml`: `images` job: builds the 5 images; Trivy fails on fixable HIGH/CRITICAL.
- `scripts/pin-image-digests.sh` (new): pins `FROM` to `tag@sha256` (not run: Docker Hub unreachable here).

## R-15 / F-12: CSP (f50879b)
- `frontend/scripts/postbuild.mjs`: adds `style-src-elem 'self'` and `style-src-attr 'unsafe-inline'`.
- `frontend/tests/e2e/csp.spec.js` (new, 14 tests): every page under the built CSP has 0 violations; an injected
  `<style>` is blocked.

## R-3 / F-03: backups (a791575)
- `deploy/backup/crtdh-backup.sh`, `crtdh-restore-check.sh`, `backup.conf.example`, `README.md` (new).
- `tests/tools/test_backup_scripts.sh` (new, 13 checks). `docs/HANDOVER.md`, `deploy/README.md` point to them.
- Security: AES-256 GPG, files mode 600, passphrase file must be 600, plaintext only in a temp folder during
  verification, removed after. Read-only against the running stack.

## R-6 / F-08: E2E (be95d37, ea9edc7)
- `tests/e2e/test_cms_editor.py`: the restore spec creates its own published version
  (`helpers.ensure_published_version`); `test_hero_upload_rules` rewritten for the simplified photo field.
- `tests/e2e/helpers.py`: publish helpers moved here from `test_publish_flow.py`.
- `scripts/preprod.sh`: `MFA_ENABLED=True` (production setting; all E2E sign-ins expect a code).
- `tests/e2e/golden/public_content.json`: headings re-baselined to the restored design; previous file kept.
- `frontend/src/site/pages/Home.jsx`: hero slides without a photo are left out (they rendered `<img>` with no src).
- `backend/requirements-dev.txt`: `axe-playwright-python==0.1.8` (the accessibility E2E imported it, but nothing
  installed it).
- **Root cause of the restore failure:** the precondition read the wrong key (`results` vs `snapshots`), so an empty
  history was not noticed; the spec runs before the publish spec on a fresh stack.

## R-16 / F-13: no code change (40ff3c6, reverted by 2d7f87d)
- I first switched the PIB link to https in the seed fixture. That broke
  `test_first_snapshot_reproduces_todays_content`: the seed must equal the live content as published. Reverted.
  The two http links are content and are fixed in the CMS (checklist §7). uniindia's https URL returned a client
  error from here, so check it by hand before changing it.

## Golden fix (2453bdc)
- `tests/e2e/golden/public_content.json`: `/media` keeps "Media coverage". The first re-capture ran on a
  rehearsal whose coverage links an earlier E2E run had emptied.
