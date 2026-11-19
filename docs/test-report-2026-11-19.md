# CRTDH v3 test report: 19 Nov 2026 (FINAL confirmation run)

**Tree:** `v3/qa` at the merge of `v3/integration` e1b4a3b (merge commit ec511d9). That head carries the fixes for D1–D11 and D13, and the deploy blockers B1–B7 (worker image with Node + `deploy/worker/build-site.sh`, Access service token in the agent, both Anthropic IP ranges, admin globals, Claude-access screen, `cleartokens`).
**Environment:** QA sandbox. The preprod rehearsal was wiped and rebuilt from scratch (`preprod.sh down --wipe`, fresh `npm ci`, fresh admin build) and ran with production settings: `DEBUG=False`, HTTPS with a self-signed cert, PostgreSQL 16.15, gunicorn, MCP under uvicorn `--no-proxy-headers`, a trusted-proxy rule allowing only the local gateway, the publish worker building with `deploy/worker/build-site.sh` (as the worker image does), a fake CIC SFTP host and the real publish agent. `check --deploy`: only W021 (HSTS preload, deliberate).
**Evidence:** `docs/test-evidence/2026-11-19/`. Every number below comes from a file there. The wave-2 report is in git history (18313af).

## FINAL go / no-go by level

| Level | Result (final run) | Go? | Evidence |
|---|---|---|---|
| Unit + SIT | Backend `--integration`: **1242 passed** on SQLite and **1242 passed** on PostgreSQL 16. Publish agent: **92 passed**. Gates: ruff clean, import-linter 2/2 kept, write-path check ok, MCP tool schema unchanged (26 tools). | **GO** | backend-sqlite.txt, backend-postgres.txt, publish-agent.txt |
| Preprod rehearsal / smoke | `up` and `smoke` pass on a wiped stack: production posture, CSP, MCP behind OAuth, publisher password + TOTP, draft not live, review list, publish → fake CIC host → live check against the build marker → live folder serves the change. | **GO** | preprod-smoke.txt |
| E2E (Playwright, 209 cases) | **207 passed, 0 failed, 2 skipped.** Public site 161/161 incl. overflow, fonts, SEO, Indic names, home JS budget; CMS editor 7/7; publish flow 3/3 run; MCP connector 6/6 (OAuth + PKCE + TOTP + consent + tools + upload link + session cap); contact validation + mailto fallback. Skipped: contact *send* (live Turnstile unreachable) and agent-offline (needs the agent stopped; passed on its own in wave 2). | **GO** | e2e-final.txt, e2e-final-junit.xml |
| CRITICAL regression 1: content kept after the prerender switch (golden) | **25/25 pass** (headings × 12, items × 12, every published image rendered). D13 content verified on the live preprod pages word for word: figures strip with 4 figures incl. "Researchers & staff", the three Explore descriptions, the three captions, the PI "Research Leadership — Guiding CRTDH's vision…" line, Team intro heading, tagline "Research. Innovation. Collaboration. Impact." + "Get in Touch". **Nothing is missing.** | **GO** | e2e-final.txt (golden block), tests/e2e/golden/public_content.json |
| CRITICAL regression 2: the first snapshot reproduces today's DB | 25 collections plus singletons match (part of the backend run). | **GO** | backend-postgres.txt |
| Security | semgrep project rules: **0 ERROR**, 1 WARNING (triaged false positive: `mcp_server/evals/run.py:121` uses `httpx.AsyncClient(timeout=120)`; eval tooling, not shipped). npm audit `--audit-level=high`: **0 vulnerabilities** (frontend and admin, all deps incl. dev). pip-audit: **0** (backend with `--require-hashes`, agent). bandit `-ll -ii`: **0 medium/high**. gitleaks on HEAD (tracked files via `git archive`, not history): **no leaks**. Product checks from wave 2 (headers/cookies 0 FAIL, attack pass 32/32, SSRF 12/12) not re-run; nothing in the D7–D13 fixes touches those paths. | **GO** (CI security gate now green) | security/semgrep.txt, npm-audit-*.txt, pip-audit-*.txt, bandit.txt, gitleaks-head.* |
| Performance | Home JS budget (≤150 KB gzip) passes in E2E on the worker-built site. LCP/CLS numbers are from wave 2 (Home 1.7–1.8 s, CLS ≤ 0.008 on Slow-4G + 4x CPU); not re-measured. | **GO** | e2e-final.txt (test_home_js_budget), perf.json |
| Accessibility (axe, 375 and 1280) | **50 screens, 0 serious/critical**: public 13 pages × 2 widths, admin 12 screens × 2 widths (login, MFA, 5 page editors, review, history, users, messages, shot list). D9 fixed. Moderate/minor only: landmark-unique (/about), image-redundant-alt (/innovations, /facilities), landmark-main-is-top-level (/shot-list), and on /pages/team at 1280 landmark-one-main + page-has-heading-one + region (moderate; worth a look, not blocking). | **GO** | a11y.txt, a11y.json |
| QA exploratory | Wave 2 charters (keyboard-only sign-in, editor at 375 px, upload machine off/on, restore) not re-run; no change since touches those flows beyond what E2E re-covers. | **GO** | explore/notes.txt |
| Simulated UAT | Every **must** step in docs/uat/ is covered by a passing E2E spec. | **Simulated only — not sign-off** | docs/uat/ |
| Real infrastructure | See the list below. | **Not verifiable here — must be done at go-live** | — |

**Overall: GO for deployment to the real infrastructure.** Every level that can run in the sandbox is green on a clean rebuild. Go-live still depends on the real-infrastructure checks listed below and on real staff UAT; those cannot be signed off from here.

## Defects

| ID | Sev | Owner | Status | Summary |
|---|---|---|---|---|
| D1 | CRITICAL | backend-core | **fixed** 4be8d65, verified | `select_for_update()` + `select_related` → Postgres "FOR UPDATE … nullable side of an outer join". The agent could never download a build. |
| D2 | HIGH | backend-core, publish-agent | **fixed** 4be8d65, verified | A publish stuck in `uploading` could not be cancelled and never timed out. |
| D3 | HIGH | deploy/gateway | **fixed** 766ec90, verified | Gateway CSP `frame-src` blocked the editor's same-origin `/preview.html`. |
| D4 | CRITICAL | publish-agent | **fixed** dcac9e5, verified | Live check compared the sanitised snapshot id with the raw marker, so every publish rolled back. |
| D5 | CRITICAL | mcp (apps.oauth) | **fixed** 4534820, verified | `no-referrer` on the consent page → `Origin: null` → CSRF 403; no connector could connect. |
| D6 | HIGH | admin | **fixed** 0820973, verified | Two copies of React in the canvas; editor canvas blank. |
| D7 | LOW | admin | **fixed** 4c959d2, verified | Semgrep ERROR in the admin site shim (shim deleted). semgrep now 0 ERROR. |
| D8 | MEDIUM | frontend, admin | **fixed** ff0f629, verified | npm audit high/critical in dev tooling. Now 0 in both. |
| D9 | MEDIUM | admin | **fixed** 0a5845d, verified | axe critical `button-name` on `.user-btn` at 375 px. Now 0 serious/critical on every admin screen. |
| D10 | MEDIUM | frontend/design | **closed** (owner decision + D13) | Home figures and Team intro restored; role badges removed by design (golden re-baselined). |
| D11 | MEDIUM | backend-core / backend-security | **fixed** 04f85c8, verified by its backend tests (SMTP failure no longer fails the request); the outage path was not forced on preprod | `request_review` hard-failed when email could not be sent; `EMAIL_FILE_PATH` ignored. |
| D12 | LOW | mcp / backend-core | **open — known gap, accepted for launch** | `search_media` matches stored hash file names, so words from the original upload name never match. Identical bytes uploaded twice are stored twice (`<hash>_xxxx.jpg`). No data loss or security impact; affects findability and some storage. |
| D13 | MEDIUM | frontend | **fixed** e1b4a3b, verified | Old Home/Team content restored (4 figures, Explore descriptions, captions, PI line, Team tagline + Get in Touch). Golden 25/25. |
| — | LOW | product design | note | Per-user MCP write rate (20/min) trips before the per-session cap (25). Both are guardrails; not a defect. |

## Attack pass (wave 2, preprod, report-only; not re-run in the final run)

All 32 probes held. The summary:
- **Direct port access:** requests to :8600 and :8601 from a non-proxy peer get 403.
- **Spoofed headers:** a spoofed CF-Connecting-IP still needs OAuth.
- **MFA:**
  - A password-only session can't read or write content (401).
  - A TOTP code replayed within the same 30 s step is refused.
  - Brute force on the code is locked out after 4 wrong codes (429), and the account stays locked even with the right code.
- **CSRF:** a write without the token, or with the token from a foreign Origin, gets 403.
- **IDOR / vertical privilege:** an editor is refused contact messages, users, role changes, publish and delete. Self-promotion through `/auth/me` gets 405 and the role is unchanged.
- **Uploads:**
  - A JPEG+HTML polyglot, an SVG with script, and a GIF header with script are all refused.
  - A traversal file name is neutralised.
  - Upload links work once only.
- **Path traversal:** 5 CMS media traversal variants and 3 static-host variants get 404.
- **Draft media:** needs a session.
- **SSRF (MCP fetch):**
  - Blocked: http://, bare IPs including v6 and metadata, localhost, hex/decimal IP hosts, localtest.me, file://, gopher://, and userinfo URLs.
  - Not proven here: DNS rebinding against an allow-listed host. The MCP unit tests cover it with an injected resolver.


## Can only be verified on real infrastructure (before or at go-live)

None of these can run in the sandbox; each must be done once on the real setup and recorded.

| Item | Why not here | What to do |
|---|---|---|
| **Docker images** (cms, mcp, worker with Node + `build-site.sh`, agent, gateway) | No Docker daemon in the sandbox. Preprod runs the same commands natively (the worker calls `deploy/worker/build-site.sh` as the image does). | Build every image from a clean checkout, `docker compose up` with the prod compose file, confirm `--require-hashes` installs, run `scripts/preprod.sh smoke` (or its steps) against it. |
| **nginx gateway** | The rehearsal gateway is a Python stand-in; nginx config was reviewed statically. | `python tests/tools/check_headers.py --cms https://<cms host> --user <publisher>`: 0 FAIL; confirm the trusted-proxy rule (direct :8600/:8601 → 403), `/static/` from collectstatic, `frame-src` for `/preview.html`. |
| **Cloudflare Tunnel + Access** | External service. | CMS reachable only through Access; the agent's Access service token works; CF-Connecting-IP handling; a request that bypasses the tunnel is refused. |
| **Real institute server** (CIC / academicweb SFTP + Apache) | No access from here; preprod uses a fake SFTP host. | One real publish; `check_headers.py --site https://<public site>` (`.htaccess` honoured); rename/switch semantics; quota; one rollback (PLAN §9 first-5-minutes). |
| **Real claude.ai connector** | No claude.ai account or public MCP hostname here; Anthropic IP ranges not reachable. | Connect from claude.ai through Anthropic's cloud to the MCP hostname (both IP ranges allow-listed); run `docs/uat/connect-claude-timing.md` C1–C9 including the Claude-access screen and `cleartokens`. |
| **Real staff UAT** | Needs the people. | Editor and publisher sheets in `docs/uat/`, run type **Real staff**; the simulated runs here are not sign-off. |
| **Live Turnstile** | Widget + siteverify unreachable; the E2E contact *send* is skipped (test key + mocked verify only). | Send one real contact message; confirm a failing token is refused and the message arrives by real email. |
| **ZAP baseline** (and semgrep registry packs) | ZAP needs Docker; semgrep.dev is blocked by the proxy. | `scripts/security/zap-baseline.sh https://<public site>` and against the CMS: no FAIL rule, Medium alerts triaged. Registry packs run in CI. |
| **Real email delivery** | Mail goes to a local SMTP sink. | Request review sends the Publisher email; a forced SMTP failure still records the review request (D11). |

## Harness changes made during wave 2 (QA-owned)

- **Rehearsal stack:**
  - preprod gets the trusted-proxy rule, `CONTACT_API_URL`/`SITE_URL` for the worker build, a Claude OAuth client, and an SMTP sink.
  - The rehearsal gateway now matches nginx: Host passes through, `/cms/login` goes to Django, `/static/` is served from collectstatic.
  - The static host does TLS handshakes per connection. Before this, Chrome dropped some CSS, which produced false overflow/font failures.
- **E2E browser and specs:**
  - The E2E browser can only reach the local stack. A real OAuth code had reached claude.ai once before this change, because Playwright's route() does not see redirect hops.
  - CMS editor, publish-flow and MCP specs were rewritten against the delivered UI and tool shapes.
  - The golden is captured in a subprocess.
  - Specs are seed-aware.
- **Hygiene:** `Stack` no longer prints passwords or TOTP secrets in tracebacks.
- **Evidence location:** pytest-playwright wipes `./test-results`, so evidence lives in `docs/test-evidence/`.
- **Note:** earlier v3/qa commits aa863ac and 9e8e3c6 contain throwaway TOTP secrets of rehearsal users (database since wiped). They are redacted at HEAD; squash or rewrite before merging if a clean history scan is wanted (lead's call).

## Harness changes made in the final run (QA-owned)

- **Golden run order:** `tests/e2e/conftest.py` now runs `test_golden_regression.py` right after the harness check, before the specs that change content on purpose. Before this, the editor spec deleted every Media coverage link and the publish specs published that, so the golden reported "Press coverage" and 8 press links as lost (a test artefact, not a product defect; first-run evidence kept in `e2e-final-before-golden-order-fix.txt`).
- **Hero headline:** the smoke and publish specs write a marker into the first hero headline. The golden spec now maps those markers back to the seed headline before comparing headings, and the golden `/` h1 is the seed text ("Common Research & Technology Development Hub") instead of a captured smoke marker.
- **Golden `/` headings:** "Explore CRTDH" added (it came back with the D13 restore; an addition, not a loss).
- **gitleaks on HEAD** scans `git archive HEAD` (tracked files only). A plain `gitleaks dir .` also picks up the gitignored `.preprod/` runtime keys and passwords of the throwaway rehearsal stack.
