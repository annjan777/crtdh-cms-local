# Testing CRTDH v3

What each test level proves, how to run it, when it may start (entry) and when it is done (exit).
Owner: QA lane. CI: `.github/workflows/ci.yml` (job names in brackets). Python commands use the backend venv
(sandbox: `/home/claude/venv/bin/python`); run from the repo root unless a directory is given.

## Levels

| Level | Proves | Command | CI job | Entry | Exit |
|---|---|---|---|---|---|
| **Unit** | models, serializers, snapshot builder, guard, auth/MFA, MCP tool logic, publish agent pieces, frontend components | `cd backend && pytest` · `python -m pytest publish_agent/tests -p no:asyncio` · `cd frontend && npm test` | backend, frontend | code compiles; `ruff check .` clean | all pass; no new skip without a reason; coverage report attached (no hard threshold) |
| **SIT** (system integration) | lanes work together: CMS API ↔ publishing ↔ snapshot schema ↔ frontend build ↔ MCP ↔ agent; RBAC matrix (anon/editor/publisher/admin × every route, ~690 cases); contract error bodies; the two CRITICAL regressions | `cd backend && pytest --integration` (also `TEST_DATABASE_URL=postgres://… pytest --integration --create-db`) · `cd backend && lint-imports` · `python tests/tools/write_paths.py` · `python tests/tools/mcp_schema.py --check` | backend | all lanes merged into `v3/integration`; migrations apply on an empty DB | 0 failures on SQLite **and** Postgres 16; import contracts kept; MCP schema diff reviewed |
| **E2E** | a person's path through real browsers: edit → autosave → preview → not live → publish → live; stale-save conflict; Claude connector OAuth + TOTP → tools; contact form; 12 public routes (content without JS, no API calls, golden regression vs the pre-v3 SPA) | against preprod: `scripts/preprod.sh up && scripts/preprod.sh e2e` · self-started stack: `python -m pytest tests/e2e --integration` (needs built `frontend/build/client` and `admin/dist`) | e2e | SIT green; public site and admin build | all specs pass; traces/screenshots of any failure attached; golden diffs = 0 |
| **QA exploratory** | what scripts miss: odd inputs, confusing copy, states between steps | 60-min charters on preprod, notes in `test-results/exploratory-<date>.md`; charters: (1) editor on a phone, (2) two people editing at once, (3) Claude given a hostile page text, (4) upload machine off/on mid-publish, (5) restore + republish an old version | — (manual) | E2E green on preprod | every charter run once; each bug filed with steps; no open P1 |
| **Security** | SAST, dependencies, secrets, headers/cookies/CSP, passive DAST; RBAC and SSRF/upload regressions live in SIT (`-m security`) | `pip-audit -r backend/requirements.txt --require-hashes` · `bandit -r backend/apps backend/mcp_server publish_agent -x '*/tests/*,*/migrations/*' -ll -ii` · `scripts/security/semgrep.sh` · gitleaks (CI) · `python tests/tools/check_headers.py --cms https://localhost:8600 --ca .preprod/tls/cert.pem --user priya` · `python tests/tools/check_headers.py --htaccess frontend/build/client/.htaccess` · `scripts/security/zap-baseline.sh https://localhost:3601` | security, frontend (htaccess), e2e (headers) | SIT green | no High/Critical CVE; no bandit/semgrep ERROR (or a `nosec`/`nosemgrep` with a written reason); gitleaks clean; header check 0 FAIL; ZAP baseline no FAIL rule; Medium ZAP alerts triaged |
| **Performance** | budgets that matter at this scale (one lab, 12 pages, ≤20 editors): home JS ≤ 150 KB gzip, prerendered HTML, long-cache headers on hashed assets | `cd frontend && npm run size` · E2E `test_home_js_budget` · `check_headers.py --htaccess` (Cache-Control) | frontend, e2e | build green | budgets met. No load test: not warranted for this traffic; revisit only if the site moves off static hosting |
| **Accessibility** | public pages: axe-core no serious/critical, landmarks + skip link, no horizontal overflow at 375/768/1280, long and Indic names fit | E2E `-m a11y` and `test_no_horizontal_overflow` | e2e | E2E green | 0 serious axe violations on 12 routes × 3 widths; admin: one manual keyboard-only pass (Tab through editor, review, publish) recorded in the exploratory notes |
| **Simulated UAT** | the UAT run sheets can be completed step by step | `docs/uat/*.md` run by QA on preprod, every sheet marked **Simulated** | — | E2E green | every **must** step passes; questions/confusions listed for the real run. Never counts as sign-off |
| **Preprod rehearsal** | the production configuration end to end on one machine: `DEBUG=False`, HTTPS (self-signed), Postgres 16, gunicorn, MCP uvicorn, publish worker, fake CIC SFTP host, publish agent, `check --deploy` | `scripts/preprod.sh up` → `smoke` → `e2e` → `down` (`status` any time; logs in `.preprod/logs/`) | e2e | integrated tree (`up` refuses otherwise) | smoke all PASS (edit → publish → live folder serves the change with the build marker); `check --deploy` only W021 (HSTS preload, deliberate) |

Markers: `needs_integration` (skipped unless `--integration` or `RUN_INTEGRATION=1`), `security`, `contract`,
`regression_critical`, `slow`; E2E also `a11y`, `visual`, `perf`, `mcp`.

## Gates added in CI (wave 1)

- **ruff** (`ruff.toml`): correctness only (syntax, undefined names, unused/redefined imports). Style is not gated.
- **import-linter** (`backend/.importlinter`): `mcp_server` may reach content models only through
  `apps.publishing`; `apps.publishing` never imports `mcp_server`.
- **write paths** (`tests/tools/write_paths.py`): every writable content-app viewset uses `CMSResourceMixin`; no
  direct ORM writes in content-app views or `apps/common/mixins.py` (exception: `# write-path: ok <reason>`).
- **MCP tool schema snapshot** (`tests/golden/mcp_tools.json`, 24 tools, captured from `v3/mcp` d39eb4e): any
  change to tool names, descriptions, input schemas or annotations shows as a diff; refresh with
  `python tests/tools/mcp_schema.py --write` in the same PR.
- **semgrep** (`tests/security/semgrep-crtdh.yml` + registry packs): project rules for stored XSS
  (`mark_safe`, `dangerouslySetInnerHTML`), `csrf_exempt` scope, `AllowAny`, shell, timeouts, MCP fetches only via
  `mcp_server/fetch.py`, raw SQL, TLS verify off, SFTP host-key auto-accept, `DEBUG = True`.
- **actionlint** validated the workflow (v1.7.7 with shellcheck): clean.

## What cannot run in the sandbox

| Item | Why | How it gets covered |
|---|---|---|
| The real institute server (CIC / academicweb SFTP, Apache `.htaccess`, quota, rename semantics) | no access from here | fake SFTP host in preprod; once on the real host: one publish, `check_headers.py --site https://<public site>`, rollback test, quota check (PLAN §9 first-5-minutes) |
| The real Claude connector (claude.ai → Anthropic cloud → our MCP hostname) | no claude.ai account, no public hostname (gate d5), Anthropic IP range not reachable | `test_mcp_connector.py` drives OAuth/TOTP/consent and the tools with the MCP SDK client; real run = `docs/uat/connect-claude-timing.md` C1–C9 |
| Real staff UAT | needs the people | `docs/uat/` sheets, run type **Real staff** |
| semgrep registry packs, ZAP Docker image | proxy blocks semgrep.dev; no Docker daemon | offline project rules run here (`SEMGREP_OFFLINE=1`); both run in CI |
| Cloudflare Tunnel / Access, Turnstile live verify, real email delivery | external services | Turnstile always-pass test key + mocked verify; emails to the file backend (`.preprod/mail`) |

## Tests waiting on integration (`needs_integration`)

Backend (`cd backend && pytest --integration`), 743 cases collected on the QA tree (the RBAC count follows the merged router):

- `tests/security/test_rbac_matrix.py` — `test_rbac` (688 role × route cases), `test_every_router_resource_is_in_matrix`, `test_only_public_write_is_contact`, `test_deactivated_user_session_stops_working`
- `tests/regression/test_first_snapshot.py` (CRITICAL) — `test_schema_and_header`, `test_every_collection_present`, `test_rows_and_values_match` ×25, `test_singletons_match`, `test_media_paths_are_content_hashed`
- `tests/contract/test_snapshot_rules.py` — schema validation, ordering, stable ids, hidden item absent, same snapshot twice, guard (missing collection, 40 % shrink), every route has a registry page
- `tests/security/test_contact_relay.py` — valid message, Turnstile failure 400, 6th/min 429, HTML stored escaped, contact is the only anonymous write
- `tests/security/test_ws0_hardening.py` — prod settings fail closed ×5 / start when sane, seed fixture has no users, prod compose does not reseed, deploy env not tracked, no default admin password

E2E (`scripts/preprod.sh e2e` or `pytest tests/e2e --integration`), 216 cases:

- `test_golden_regression.py` (CRITICAL) — headings / items / images unchanged × 12 routes
- `test_public_site.py` — prerendered content, no CMS API calls, content without JS, landmarks, axe, overflow (×36), visual baseline + fonts (×36), SEO meta, placeholder sweep, sitemap, 404, Indic names, team page, home JS budget
- `test_cms_editor.py` — autosave/preview/not live, stale save two tabs, request review + publisher email, review & publish, restore confirmation, hero upload rules, empty collection CTA
- `test_publish_flow.py` (needs `E2E_PUBLISH_STACK=1`, set by `preprod.sh e2e`) — edit → publish → static changed, state sequence, double click = one build, agent offline = waiting
- `test_mcp_connector.py` — tools listed with hints, find → update → preview → not live, stale version, upload link → add hero slide, session write cap, request review → publisher publishes
- `test_contact_form.py` — blur validation + send, relay down shows mailto

Already checked ahead of the merge (QA copies of lane heads, 19 Nov): RBAC matrix + first-snapshot regression +
snapshot contract = **728 passed** on `v3/backend-core` 337ab45; contact relay and WS0 hardening need
`v3/backend-security` merged.
