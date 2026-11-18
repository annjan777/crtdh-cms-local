# CRTDH v3 — shared contracts (owned by the lead; change only through the lead)

Plan: `/home/claude/team/PLAN.md` (Implementation plan section is the source of truth). Test plan: `/home/claude/team/TEST-PLAN.md`.
Every workstream codes against this file. If you need a change, write it in `/home/claude/team/inbox/lead.md` and keep working with a local adapter; do not silently diverge.

## 1. Snapshot (the only input to the public build)
File `snapshot.json`, produced by `apps.publishing.snapshot.build_snapshot()`; JSON Schema at `backend/apps/publishing/snapshot.schema.json`.
```json
{
  "schema_version": 1,
  "snapshot_id": "2026-11-19T09:30:00Z-3f2a1c",
  "published_at": "2026-11-19T09:30:00Z",
  "published_by": "priya",
  "singletons": { "site-settings": {...}, "about-page": {...}, "home-page": {...} },
  "collections": { "<resource>": [ {row as the existing DRF list serializer returns it} ] },
  "registry": { ...section registry, §2... }
}
```
- `<resource>` keys are the existing DRF router basenames' URL names (`hero-slides`, `team-members`, `media-events`, …, see `config/urls.py`). Row shape = the current serializer output, so the public pages keep their field names.
- Only visible rows (`is_published` true where the field exists). `contact-messages` and users are never included.
- Media: every image/file URL becomes a site-relative path `/media/<sha256-prefix-16>.<ext>` (content-hashed). The snapshot also lists `"media": {"/media/<hash>.<ext>": {"source": "hero_slides/banner01.jpg", "width": 2400, "height": 1350, "variants": {"avif": [...], "webp": [...]}}}`.
- Ordering: rows sorted by `order` then `id`.
- Stub for frontend work before the backend lands: `/home/claude/team/stub-snapshot.json` (same shape minus registry/media/ids; image URLs still absolute to localhost:8000).

## 2. Section registry
`backend/apps/publishing/registry.py` — one Python list, exported to JSON by `manage.py export_registry > registry.json` and embedded in the snapshot.
```json
{ "pages": [
  { "id": "home", "path": "/", "title": "Home", "sections": [
     { "id": "home.hero", "label": "Hero", "kind": "collection", "resource": "hero-slides",
       "fields": [ {"name":"image","type":"image","required":true,"min_width":1600,"alt_field":"alt_text"},
                   {"name":"title","type":"text","max":60}, ... ] },
     { "id": "home.about", "label": "About the centre", "kind": "singleton", "resource": "home-page", "fields": [...] }
  ]},
  ... 12 pages: home, about, team, innovations, facilities, services, product, enterprises, social-impact, covid-19, media, contact
]}
```
- Item ids are stable: `<section id>.<resource>:<pk>` e.g. `home.hero.hero-slides:7` (never positional).
- Field `type` ∈ text, textarea, richtext (bold, italic, link, ul, ol, h3 only), image, url, date, number, select, boolean.
- `ImageGridBlock.page` / `VideoBlock.page` become `choices` = registry page ids.
- CI test: every public route has a registry page and vice versa.

## 3. CMS API (private origin; session cookie + CSRF; JSON)
Auth
- `POST /api/v1/auth/login/` {username, password} → 200 {mfa_required:true} or sets session; `POST /api/v1/auth/mfa/` {code} → session; `POST /api/v1/auth/logout/`; `GET /api/v1/auth/me/` → {id, username, name, roles:["editor"|"publisher"|"admin"], mfa_enrolled}
- `GET /api/v1/auth/csrf/` sets the CSRF cookie. All unsafe methods need `X-CSRFToken`.
Roles: editor (edit, request review), publisher (+ publish, restore), admin (+ users). Groups named `editor`, `publisher`, `admin`; superuser = admin.
Content (existing resource endpoints, now auth-required for every method including GET)
- `GET/POST /api/v1/<resource>/`, `GET/PATCH /api/v1/<resource>/<id>/`, `POST /api/v1/<resource>/reorder/`
- Every row exposes `version` (int). PATCH must send `expected_version` (body) → 409 if stale.
- DELETE: admin and publisher only.
CMS
- `GET /api/v1/cms/pages/` → registry pages + `{has_changes: bool}` each
- `GET /api/v1/cms/pages/<page>/` → registry page with each section's current values + versions (draft = current DB)
- `GET /api/v1/cms/preview/<page>/` → snapshot-shaped data for that page built from the current DB (for the admin canvas)
- `GET /api/v1/cms/changes/` → `{count, pages:[{page, changes:[{item_id, resource, pk, label, kind:"added"|"changed"|"hidden"|"removed", fields:[{name, before, after}], author, channel, at}]}]}` (diff of current DB vs last published snapshot)
- `POST /api/v1/cms/changes/discard/` {item_id} or {session_id} → reverts to the last published values
- `POST /api/v1/cms/review-requests/` {note} → emails publishers
- `POST /api/v1/cms/publish/` {confirm_shrink?: bool} → 202 {publish_id, status:"queued"}; single-flight (a running publish returns 409 with its id)
- `GET /api/v1/cms/publish/<id>/` → {status: queued|building|ready_for_upload|uploading|live|failed, step, message, live_at, agent_last_seen}
- `GET /api/v1/cms/snapshots/` ; `POST /api/v1/cms/snapshots/<id>/restore/` (copies values back as unpublished changes)
- `GET /api/v1/cms/audit/?item_id=` → audit entries
- `POST /api/v1/cms/upload-links/` → {url, token, expires_at} (one-time photo upload page; MCP and admin)
Publish agent (runs on the whitelisted PC; HMAC auth header `X-Agent-Signature`)
- `GET /api/v1/agent/next/` → 204 or {publish_id, tarball_url, sha256, signature}
- `GET /api/v1/agent/builds/<publish_id>.tar.gz`
- `POST /api/v1/agent/status/` {publish_id, status, step, message}
Public (separate hostname, no session)
- `POST /api/v1/contact/` (Turnstile token, throttled 5/min/IP) — the only public write.

## 4. Error body (API and MCP structured content)
```json
{ "code": "CMS_STALE_VERSION", "message": "home.hero.hero-slides:7 changed since you read it (you sent v7, current v8, edited by priya at 14:02).",
  "fix": "Reload the section and reapply your change.", "retryable": false, "side_effects": "none",
  "field": null, "current_version": 8, "request_id": "7f3a…" }
```
Codes: CMS_VALIDATION (400), CMS_UNAUTHENTICATED (401), CMS_FORBIDDEN_ROLE (403), CMS_NOT_FOUND (404), CMS_STALE_VERSION (409), CMS_PUBLISH_RUNNING (409), CMS_IMAGE_TOO_SMALL (400), CMS_FETCH_BLOCKED (400), CMS_RATE_LIMITED (429), CMS_SESSION_LIMIT (429), CMS_BUILD_GUARD (422), CMS_INTERNAL (500). Never include secrets, tokens, signed URLs or tracebacks.

## 5. Build and output
- `frontend/` builds with React Router 7 framework mode, `ssr:false`, `prerender` of the 12 routes; loaders read `SNAPSHOT_PATH` (env, default `frontend/snapshot.json`). Output `frontend/build/client/`. Pages receive data as props; no runtime API calls except the contact form.
- Build guard (`apps.publishing.guard`): schema valid; every collection present; no collection shrinks > 30% vs previous snapshot unless `confirm_shrink`.
- Tarball: `crtdh-site-<snapshot_id>.tar.gz` with `site/` (HTML/CSS/JS) and `media/` (only new hashes listed in `manifest.json`).

## 6. Ports (sandbox, per lane — never use another lane's ports)
lead 8000/3000/3001 · backend-core 8100 · backend-security 8200 · frontend 3100 (backend 8101 if needed) · admin 3200 + backend 8300 · mcp 8400 · publish-agent 8500 + sshd 2222 · qa 8600/3600/3601

## 7. Rules for every lane
- Work only in your worktree `/home/claude/wt/<lane>` on branch `v3/<lane>`; commit small, clear commits there with `git -c user.name=crtdh-build -c user.email=build@localhost commit` (never add Co-Authored-By trailers). Never push, never touch another worktree.
- Python venv `/home/claude/venv` (shared; `pip install --break-system-packages` is not needed inside it). SQLite for tests. Node deps: `npm ci` inside your worktree.
- Long-running servers: start with `setsid nohup … &` on your lane's ports and stop them when done.
- Status: keep `/home/claude/team/status/<lane>.md` current (done / doing / blocked / questions). Ask other lanes by appending to `/home/claude/team/inbox/<their lane>.md` with your lane name and time; check your own inbox at every milestone.
- Done = tests written and passing for what you built + status file updated + a final report listing commits, tests run with results, and anything not done.
- Credentials in the sandbox are local test values only. Never put real passwords in code or docs. The server password from email is never written anywhere.
