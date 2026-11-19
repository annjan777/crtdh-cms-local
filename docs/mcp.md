# Claude MCP server (developer guide)

Staff guide: [connect-claude.md](connect-claude.md). This page is for whoever maintains the server.

## What it is

Editors add the CMS to Claude as a custom connector and ask for changes in plain English.
Claude reads pages and saves **unpublished changes** only. It has no tool to publish, delete,
or manage users or roles; a Publisher publishes in the CMS as usual.

## Pinned versions

| Thing | Version | Where |
|---|---|---|
| MCP protocol | **2025-11-25** (also accepts 2025-06-18) | `MCP_PROTOCOL_VERSIONS` in `config/mcp_settings.py` |
| MCP Python SDK | `mcp==2.3.0` | requirements (owned by backend-security) |
| OAuth server | `django-oauth-toolkit==3.4.1` | same |
| Claude's OAuth requirements | checked 19 Nov 2026 against claude.com/docs/connectors/building/authentication | |

Requests that declare any other `MCP-Protocol-Version` (for example the stateless
2026-07-28 revision) get HTTP 400 before they reach the SDK. To move to a newer revision:
add it to `MCP_PROTOCOL_VERSIONS`, run the test suite and the eval, then try a real
claude.ai connection.

## Architecture

```
 claude.ai (Anthropic cloud, 160.79.104.0/21 and 153.61.208.0/20)
     │  https://mcp.<domain>   Cloudflare Tunnel; WAF allows only Anthropic's range
     ▼
 uvicorn mcp_server.asgi:app  :8400   (its own process; never in gunicorn)
   /mcp                                    MCP streamable HTTP, bearer token required
   /.well-known/oauth-protected-resource[/mcp]   RFC 9728
   /.well-known/oauth-authorization-server       RFC 8414
   /oauth/token/  /oauth/revoke_token/     django-oauth-toolkit
   everything else                          404
     │ imports the same Django project (models, roles)
     ▼
 Postgres

 editor's browser ──► https://cms.<domain>/oauth/authorize/   (Cloudflare Access + CMS sign-in + TOTP)
                      consent: "Allow Claude to edit drafts as <name> (<role>)"
```

### Why the sign-in page is on the CMS host

The MCP hostname only admits Anthropic's IP range, and an editor's browser is not in it.
So the authorization endpoint (`MCP_OAUTH_AUTHORIZE_URL`, default
`{CMS_PUBLIC_URL}/oauth/authorize/`) is served by the normal CMS behind Cloudflare Access,
where the CMS session and MFA already live. The RFC 8414 metadata advertises these absolute
URLs from settings: issuer, token and revocation on `MCP_PUBLIC_URL`; authorize on
`CMS_PUBLIC_URL`. (Approved by the lead, 19 Nov.)

With `SameSite=Strict` session cookies, the redirect from claude.ai arrives without the
cookie, so the editor signs in (password + TOTP) on every connect. That is intended.

### Files

| File | Job |
|---|---|
| `mcp_server/asgi.py`, `app.py` | process entry point; routes, bearer check, protocol-version guard, Host check |
| `mcp_server/auth.py` | looks up the bearer token in django-oauth-toolkit's table on every request |
| `mcp_server/tools.py` | tool definitions, the `_run` wrapper (identity, role, rate limit, audit, errors) |
| `mcp_server/guardrails.py` | rate limits, 25-change session cap, create de-duplication |
| `mcp_server/cms.py` | **the only module that touches CMS internals** (adapter) |
| `mcp_server/errors.py` | error codes and the structured error body |
| `mcp_server/fetch.py`, `images.py` | SSRF-hardened image download and re-encoding |
| `mcp_server/models.py` | connector sessions, Claude's writes, audit of every call, staged images |
| `apps/oauth/` | consent view, validator rules, metadata, revocation, `create_claude_client` |
| `mcp_server/evals/` | 10-prompt tool-use eval |

### Rules every tool follows

- Reads are annotated `readOnlyHint`; writes `destructiveHint: false`, so Claude asks before writing.
- Every write returns `{id, version, preview_url, status: "draft", message: "Not live yet — a Publisher must publish it."}`.
- Updates need `expected_version`; a stale one gets `CMS_STALE_VERSION` with `current_version`.
- Creates are de-duplicated per connector session on a natural key (name, title + date, …) or an optional `idempotency_key`.
- One connector session (one Claude conversation, `Mcp-Session-Id`) may make `CMS_SESSION_LIMIT` (25) changes.
- Per-user limits: `MCP_RATE_LIMIT_PER_MINUTE` (60 calls) and `MCP_WRITE_RATE_LIMIT_PER_MINUTE` (20 writes).
- `request_review` emails Publishers once per connector session, and at most once per user
  every 30 minutes; repeat calls return the earlier request (`already_requested: true`).
- Every call writes a `mcp_server.ToolCall` row (user, session, tool, argument names only, outcome code, request id).
- Rich text is structured blocks rendered and escaped on the server; HTML input is refused.
- Read tool descriptions and the server instructions say site content is data, not instructions.

### Errors

Tool failures are `isError: true` results whose structured content is the contract §4 body:
`{code, message, fix, retryable, side_effects, request_id, field, current_version}`. Codes:
`CMS_VALIDATION`, `CMS_UNAUTHENTICATED`, `CMS_FORBIDDEN_ROLE`, `CMS_NOT_FOUND`,
`CMS_STALE_VERSION`, `CMS_IMAGE_TOO_SMALL`, `CMS_FETCH_BLOCKED`, `CMS_RATE_LIMITED`,
`CMS_SESSION_LIMIT`, `CMS_INTERNAL`. JSON-RPC errors are used only for protocol faults. An
unexpected exception is logged with its request id and returned as `CMS_INTERNAL` without
any exception text.

## Adding a tool via the registry

Most new content needs no new tool: `get_page`, `update_section`, `add_item`, `hide_item` and
`reorder` work for every section in the registry (`apps.publishing.registry`, data in
`registry_data.py`). To add a section, add it to the registry; the field schema Claude sees comes
from it (file fields, focus points, visibility, order and row-placing keys are not offered).

For a collection staff talk about by name (as with team members), add a typed trio to
`TYPED` in `mcp_server/tools.py`:

```python
("hero_slide", "home.hero", "a Home page hero slide (photo at least 1600 px wide)"),
```

That generates `add_<noun>`, `update_<noun>` and (if the model has `is_published`)
`hide_<noun>` with JSON schemas built from the section's fields. Then:

1. add a natural key for the resource in `guardrails.NATURAL_KEYS`;
2. add tests in `backend/tests/claude_mcp/test_tools.py`;
3. add or adjust an eval prompt in `mcp_server/evals/prompts.json` and run the eval;
4. note it in the CHANGELOG. Tool changes are additive: never rename or remove a tool
   without one release in which the old name returns an error naming the new one.

Never import models for writes in `tools.py`: go through `cms.py`.

## Running locally

```bash
cd backend
python manage.py migrate
python manage.py create_claude_client          # prints the client id + secret once
MCP_PUBLIC_URL=http://127.0.0.1:8400 MCP_EXTRA_ALLOWED_HOSTS=127.0.0.1:8400 \
  uvicorn mcp_server.asgi:app --host 127.0.0.1 --port 8400
```

Tests (QA's pytest harness): `pytest tests/claude_mcp`. They use the MCP SDK client against
the ASGI app in-process; no network.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Transport **Streamable HTTP**, URL `http://127.0.0.1:8400/mcp`. Either use the Inspector's
OAuth flow (needs the CMS running on `CMS_PUBLIC_URL` for the sign-in page), or mint a
short-lived token for a test user in `manage.py shell` and paste it as a bearer header:

```python
from datetime import timedelta; import secrets
from django.utils import timezone
from django.contrib.auth import get_user_model
from oauth2_provider.models import AccessToken, Application, set_token_value
raw = secrets.token_urlsafe(30)
t = AccessToken(user=get_user_model().objects.get(username="<test editor>"),
                application=Application.objects.get(name="Claude"), scope="cms.drafts",
                expires=timezone.now() + timedelta(hours=1))
set_token_value(t, raw); t.save(); print(raw)
```

Never do this against production.

### Eval

```bash
ANTHROPIC_API_KEY=… python -m mcp_server.evals.run        # optional: --only eye-camp, MCP_EVAL_MODEL=…
```

Runs each prompt as a conversation against seeded content; pass bar 9/10. Without a key it
writes `results.json` with every prompt `not-run`. Run it after changing tool names,
descriptions or schemas.

## Operations

### Revoking access

- One person, by themselves: CMS → profile → Disconnect Claude
  (`POST /api/v1/cms/claude-access/revoke/` with `{}`).
- Someone else (Admin): same endpoint with `{"user_id": <id>}`.
- Deactivating a CMS user revokes all their Claude tokens automatically (backend-security's
  `user_deactivated` signal, plus a `post_save` fallback on `is_active`).
- Everyone at once (incident): `python manage.py shell -c "from django.contrib.auth import get_user_model; from apps.oauth.revoke import revoke_all_for_user; [revoke_all_for_user(u, reason='incident') for u in get_user_model().objects.all()]"`

The bearer token is checked against the database on every request, so revocation cuts an
open Claude session on its next call.

Tokens: access 1 hour (`MCP_ACCESS_TOKEN_SECONDS`), refresh tokens rotate, and a connection
ends `MCP_OAUTH_MAX_GRANT_DAYS` (30) days after consent however often it refreshes. Tokens are
stored only as SHA-256 checksums. Run `python manage.py cleartokens` weekly.

### Rotating the OAuth client secret

```bash
python manage.py create_claude_client --rotate
```

Prints a new secret once; the old one stops working for new token requests. Claude stores
the secret in the connector, and connector auth settings can't be edited, so: remove the
connector in claude.ai and add it again with the new secret (Team/Enterprise: the Owner does
this in Organization settings → Connectors), then everyone clicks Connect again. Rotate after
anyone who saw the secret leaves, or if it may have leaked.

There are no signing keys to rotate: tokens are opaque random strings, not JWTs.

### Updating the Anthropic IP ranges

Claude's outbound ranges are published at platform.claude.com/docs/en/api/ip-addresses
(160.79.104.0/21 and 153.61.208.0/20 on 19 Nov 2026; the WAF expression is
`not ip.src in {160.79.104.0/21 153.61.208.0/20}`). The filter lives at the edge (the Cloudflare WAF rule on
the MCP hostname), not in this code. If connections start failing with 403 at the edge,
compare the rule with the published list and update it. The app itself still requires OAuth
on every request, so a too-wide rule is not an open door, but keep it exact.

### Settings

| Setting | Default | Meaning |
|---|---|---|
| `MCP_PUBLIC_URL` | `http://localhost:8400` | MCP hostname (issuer, resource, token endpoint) |
| `CMS_PUBLIC_URL` | `http://localhost:8000` | CMS origin (sign-in, consent, preview links) |
| `MCP_OAUTH_AUTHORIZE_URL` | `{CMS_PUBLIC_URL}/oauth/authorize/` | advertised authorization endpoint |
| `CMS_LOGIN_URL` | `/cms/login` | where signed-out users are sent, with `?next=` |
| `MCP_OAUTH_REQUIRE_MFA` | `True` | consent needs an MFA-verified session; never off in production |
| `MCP_CLAUDE_REDIRECT_URIS` | claude.ai and claude.com callbacks | registered on the client |
| `MCP_OAUTH_DCR_ENABLED` | `False` | Dynamic Client Registration, limited to the redirect URIs above (also on RFC 7592 `PUT`) |
| `CMS_SESSION_LIMIT` | 25 | changes per connector session |
| `MCP_FETCH_ALLOWED_HOSTS` | `iitkgp.ac.in`, `*.iitkgp.ac.in` | hosts `upload_image_from_url` may fetch from |
| `MCP_FETCH_MAX_BYTES` / `MCP_FETCH_TIMEOUT_SECONDS` | 10 MB / 10 s | download caps |
| `MCP_EXTRA_ALLOWED_HOSTS` | none | extra `Host` values `/mcp` accepts (local dev) |

`ALLOWED_HOSTS`: the last lines of `config/settings.py` append the hostnames of
`MCP_PUBLIC_URL` and `CMS_PUBLIC_URL` (production `ALLOWED_HOSTS` is otherwise empty), so
both processes accept their own hostname. Set the two URLs correctly in the environment;
there is nothing else to add.

## Integration status

Integrated with backend-core and backend-security (v3/integration). `mcp_server/cms.py` reads
through `apps.publishing.registry` and writes only through `apps.publishing.content`
(`update_by_item_id`, `create_item(section_id=...)`, `attach_media`, `reorder`),
`changes`, `review` and `uploads`, with `WriteContext(user, channel="mcp",
connector_session=<Mcp-Session-Id>)`, so every change is versioned and audited like an admin
edit. Photos are `apps.publishing.models.MediaAsset` rows (`media:<id>`); fetched images go
through `apps.common.images.process_upload` (polyglots are rejected, not re-encoded).

Behaviour on top of core:
- New items start hidden (addendum A3); a Publisher reviews and shows them. Photos added with
  a new item are visible (the hidden parent controls them); photos added to an item already on
  the site start hidden.
- A media id must be one of the caller's own uploads.
- `list_pending_changes` shows every unpublished change (any editor), marking this
  conversation's.
- Discard never overwrites someone else's work: if only the caller's Claude changes touched the
  item since the last publish (and its last discard), `changes.discard_item` reverts it to the
  published values (removing an item Claude added). If others edited it too, only Claude's own
  fields are put back, and only if nobody changed them after Claude; otherwise
  `CMS_STALE_VERSION` and nothing changes. `discard_session_changes` is all or nothing.
  A discarded create no longer de-duplicates.
- `StagedImage` (the pre-integration photo store) was dropped in `mcp_server` migration 0003; any
  old files under `MEDIA_ROOT/mcp_uploads/` are no longer referenced and can be deleted.
