# HANDOVER: running the CRTDH website after 31 Jan 2027

For the developer who takes over from Annjan. It explains how the system fits together, where every secret
lives and how to rotate it, the routine jobs, the incidents you are most likely to see, and the checklist for the
handover meeting. To deploy from nothing, use [GO-LIVE.md](GO-LIVE.md). The staff guide is
[STAFF-GUIDE.md](STAFF-GUIDE.md).

## 1. Architecture

```
                              PUBLIC INTERNET
                                     │
   visitors ──► https://crtdh.iitkgp.ac.in   (CIC server academicweb.iitkgp.ac.in, Apache, STATIC FILES ONLY)
                │  prerendered HTML/CSS/JS, /_media/<hash> images, .htaccess headers
                │  no server code, no database, nothing writable
                │
                │  contact form (browser JS) ──► https://contact.<domain>/api/v1/contact/  (Turnstile)
                ▲
                │ SFTP (key login), new release folder + one atomic switch, keeps 3 old releases
                │
   ┌────────────┴──────────────────────┐
   │ CAMPUS PC 10.111.26.20             │  the ONLY machine the CIC server accepts SSH/SFTP from
   │ publish agent (publish_agent/)     │  polls the CMS every 30 s (HMAC-signed), downloads the build,
   │ keys/crtdh_publish_ed25519         │  checks its SHA-256 + signature, uploads, switches, verifies
   │ agent-secret.txt                   │  <meta name="crtdh-build">, reports live/failed
   └────────────▲──────────────────────┘
                │ HTTPS to cms.<domain>/api/v1/agent/  (Access bypass for the campus IP only)
                │
   ═════════════╪═════════════ CLOUDFLARE (TLS, Access, WAF, Tunnel) ═══════════════════════════════
     cms.<domain>      Access (email code) ──┐
     contact.<domain>  WAF rate limit ───────┤          claude.ai (Anthropic cloud)
     mcp.<domain>      WAF: Anthropic IPs only ◄────────── OAuth + /mcp tool calls
                                             │ one outbound tunnel (no inbound port on campus)
   ┌─────────────────────────────────────────┴───────────────────────────────────────────────────┐
   │ LAB SERVER: docker compose project "crtdh-cms" (deploy/docker-compose.yml)                    │
   │                                                                                               │
   │  cloudflared 172.30.80.11 ──► gateway (nginx) 172.30.80.10 ──► cms (gunicorn, Django/DRF :8000)│
   │        │                       admin SPA, /api/, /oauth/authorize/, /cms/login, /static/      │
   │        └────────────────────► mcp (uvicorn ASGI :8400): /mcp, OAuth metadata/token/revoke     │
   │                                                                                               │
   │  worker: queued publish → snapshot.json → content-hashed media → frontend build → tarball     │
   │  housekeeping (daily): purge_contact_messages, clearsessions, clear_auth_throttles            │
   │  migrate (one-shot): migrate, createcachetable, collectstatic                                 │
   │  db: Postgres 16  (volume pgdata)        media (volume media_data)   static (static_data)     │
   │  networks: internal (no internet, everything)  egress (cloudflared, cms, mcp, worker only)    │
   └───────────────────────────────────────────────────────────────────────────────────────────────┘
```

Key ideas:

- **The CMS database is the working copy. The public site only changes on publish.** A publish freezes the
  whole site into one snapshot (`apps/publishing`), builds static files from it, and hands a signed tarball to the
  agent. History means past snapshots plus the audit log. "Restore" copies a snapshot back as unpublished changes.
- **One section registry** (`backend/apps/publishing/registry_data.py`) drives the admin pages and sections, the
  Claude tools and the public routes. To add a section, edit the registry (see `docs/mcp.md` → "Adding a tool via
  the registry").
- **Pull, not push.** Only the campus PC may talk to the CIC server, so it fetches builds. No credential for the
  CIC server exists anywhere except on that PC.
- **App processes trust only the gateway and cloudflared.** `REQUIRE_TRUSTED_PROXY` and `TRUSTED_PROXY_IPS`
  refuse any other peer, even from the server itself.
- Detail docs: `deploy/README.md` (stack and network), `publish_agent/README.md` (agent), `docs/mcp.md`
  (Claude/MCP), `API_CONTRACT.md` and `docs/contracts/` (API), `docs/testing.md` (tests),
  `frontend/DESIGN.md` (design rules), `docs/cms-mapping.md` (old admin screens → new editor).

### Server facts (fill in at go-live, GO-LIVE step 5.3)

| Fact | Value |
|---|---|
| CIC account user | |
| Web root | |
| Switch strategy in use (symlink / htaccess / swap / copy) | |
| Server host-key fingerprint | |
| `passwd` allowed / `authorized_keys` allowed | |
| Free space at go-live | |
| PHP/Python on the server | |
| HTTPS on crtdh.iitkgp.ac.in | |
| Campus egress IP (Access bypass) | |
| Lab server OS / path | `/srv/crtdh/app` (GO-LIVE default) |
| Institute web rules (GIGW etc.) | |
| `<domain>` and registrar | |

## 2. Where every secret lives and how to rotate it

Rule: secrets live only in the places below and in the lab's password manager. Never in git, email or chat.

| Secret | Lives in | Rotate | Effect of rotating |
|---|---|---|---|
| `SECRET_KEY` | lab server `deploy/.env` | new value (`python3 -c "import secrets; print(secrets.token_urlsafe(64))"`), then `docker compose up -d` | everyone is signed out |
| `POSTGRES_PASSWORD` (+ `DATABASE_URL`) | `deploy/.env` | `docker compose exec db psql -U crtdh -d crtdh -c "ALTER USER crtdh PASSWORD '<new>';"`, then update both variables and `docker compose up -d` | none if both are changed together. The `POSTGRES_PASSWORD` env only applies when the volume is first created |
| `AGENT_HMAC_SECRET` | `deploy/.env` **and** the campus PC's `agent-secret.txt` | change both, `docker compose up -d`, restart the agent task | the agent gets 401 until both match |
| `CMS_INTERNAL_SECRET` | `deploy/.env` | new value or empty, `docker compose up -d` | none for normal use |
| `TURNSTILE_SECRET` / `TURNSTILE_SITE_KEY` | `deploy/.env` (the site key is baked into the build) | Cloudflare → Turnstile → widget → Rotate secret key; update `.env`; `docker compose up -d`; publish once | messages fail between the two steps |
| `EMAIL_URL` (SMTP password) | `deploy/.env` | change at the provider, update, `docker compose up -d` | alerts stop until updated |
| Claude OAuth client secret | hashed in the DB; plaintext only in the password manager and the Claude connector | `docker compose run --rm cms python manage.py create_claude_client --rotate`; remove and re-add the connector in Claude (Team: Owner does it); everyone clicks Connect | existing connections end at their next token refresh |
| Claude access/refresh tokens | DB (SHA-256 only) | per user: Admin deactivates the user, or revoke (`docs/mcp.md` → Revoking access); everyone: the shell one-liner in `docs/mcp.md` | that user's Claude stops on its next call |
| Tunnel credentials | `deploy/cloudflared/credentials.json`; account cert `~/.cloudflared/cert.pem` on the lab server | `cloudflared tunnel create` a new tunnel, re-route the 3 DNS names, swap the files, `docker compose up -d cloudflared`, delete the old tunnel | a minute of downtime for cms/mcp/contact |
| CIC SFTP key | campus PC `keys/crtdh_publish_ed25519` (+ public line in the server's `~/.ssh/authorized_keys`) | `python -m publish_agent keygen keys/crtdh_publish_ed25519.new`, add the new public line on the server, point `key_file` at it, run `check`, remove the old line | none if done in that order |
| CIC account password | password manager only | `ssh` from the campus PC, `passwd` | none for the agent if it uses the key |
| CMS user passwords + TOTP | each person; Admin can reset | **Users** → Reset password / Reset two-step sign-in | that user is signed out |
| Admin recovery codes | password manager | sign-in screen, or `POST /api/v1/auth/mfa/recovery-codes/` | old codes stop working |
| Cloudflare, GitHub, registrar, AWS logins | password manager, with 2FA | in each service | — |

Rotate everything on this list when someone with access leaves, or if a secret may have leaked. The old
`admin`/`adminpassword` hash is in public git history: never reuse that name/password pair.

## 3. Routine operations

All commands run on the lab server in `/srv/crtdh/app/deploy` unless stated otherwise.

### Backups (state = the `pgdata` and `media_data` volumes; `deploy/.env` too)

Daily, from cron (`crontab -e`). Keep 14 days locally and copy them off the server (lab NAS or drive):

```bash
cd /srv/crtdh/app/deploy
D=$(date +%F)
docker compose exec -T db pg_dump -U crtdh -d crtdh | gpg --batch --symmetric --passphrase-file ~/.crtdh-backup-pass -o /srv/crtdh/backups/db-$D.sql.gpg
docker run --rm -v crtdh-cms_media_data:/data:ro -v /srv/crtdh/backups:/backup alpine \
  tar czf /backup/media-$D.tar.gz -C /data .
gpg --batch --symmetric --passphrase-file ~/.crtdh-backup-pass -o /srv/crtdh/backups/media-$D.tar.gz.gpg /srv/crtdh/backups/media-$D.tar.gz \
  && rm /srv/crtdh/backups/media-$D.tar.gz
find /srv/crtdh/backups -name '*.gpg' -mtime +14 -delete
```

`-T` matters: without it, `docker compose exec` may allocate a TTY and corrupt the dump. (The example in
`deploy/README.md` leaves it out.) Keep `~/.crtdh-backup-pass` mode 600, with a copy in the password manager.
Without it the backups are useless. The CIC side is backed up by the releases the agent keeps, plus the
`state/backups/` tarball on the campus PC.

### Restore drill (once a term, and after any big upgrade)

Restore into a throwaway Postgres, never into the live one:

```bash
docker run -d --name crtdh-restore-test -e POSTGRES_PASSWORD=drill -e POSTGRES_USER=crtdh -e POSTGRES_DB=crtdh postgres:16-alpine
sleep 5
gpg --batch --decrypt --passphrase-file ~/.crtdh-backup-pass /srv/crtdh/backups/db-<date>.sql.gpg \
  | docker exec -i crtdh-restore-test psql -q -U crtdh -d crtdh
docker exec crtdh-restore-test psql -U crtdh -d crtdh -c "select count(*) from auth_user;" \
  -c "select max(published_at) from publishing_snapshot;"
docker rm -f crtdh-restore-test
```

Pass: the counts look right and the last published date matches **Publish history**. For media:
`gpg -d media-<date>.tar.gz.gpg | tar tz | head` should list files.

Real restore (disaster): `docker compose stop cms mcp worker housekeeping gateway`, then
`docker compose exec -T db psql -U crtdh -d postgres -c "DROP DATABASE crtdh;" -c "CREATE DATABASE crtdh OWNER crtdh;"`,
pipe the decrypted dump into `docker compose exec -T db psql -U crtdh -d crtdh`, untar the media into the
`crtdh-cms_media_data` volume, then `docker compose up -d`.

### Updates

```bash
cd /srv/crtdh/app && git pull && git log --oneline -3
cd deploy && docker compose up -d --build      # migrate runs first; then the apps restart
docker compose ps && docker compose run --rm cms python manage.py check --deploy
```

Take a backup first. Migrations move forward only, so rolling the code back after a migration means restoring
the database too. To update the publish agent, copy the new `publish_agent/` folder onto the campus PC and
restart the task.

### Dependency audits (monthly; CI also runs them on every push)

```bash
pip-audit -r backend/requirements.txt --require-hashes
cd frontend && npm audit --omit=dev; cd ../admin && npm audit --omit=dev
bandit -r backend/apps backend/mcp_server publish_agent -x '*/tests/*,*/migrations/*' -ll -ii
```

`backend/requirements.txt` is hash-pinned. Edit `requirements.in`, then regenerate with
`pip-compile --generate-hashes`. Base images: bump `postgres:16-alpine`, `python:3.12-slim`, `node:20-alpine`
and `nginx:1.27-alpine` when they reach end of life. Pin `CLOUDFLARED_IMAGE` to a newer digest every few months
(GO-LIVE step 3).

### Certificates, tunnel, domain

- TLS certificates for `cms./mcp./contact.` are Cloudflare edge certificates and renew automatically. There is
  no origin certificate (the tunnel speaks HTTP inside the server).
- The tunnel credentials don't expire. cloudflared runs with `--no-autoupdate`, so update it by changing the digest.
- The **domain** registration does expire: put auto-renew on, and the renewal email on a role mailbox.
- The **public site's** certificate (`crtdh.iitkgp.ac.in`) is the CIC's. Tell them if it lapses.
- Anthropic's IP ranges: check platform.claude.com/docs/en/api/ip-addresses each term, and update the WAF rule
  (GO-LIVE 2.6).

### Other regular jobs

- Weekly: `docker compose run --rm cms python manage.py cleartokens` (expired OAuth tokens; `docs/mcp.md`). The
  `housekeeping` loop doesn't run it, so add it to cron.
- Contact messages are deleted after `CONTACT_RETENTION_DAYS` (365) by `housekeeping`.
- People: an Admin uses **Users** to add people, reset passwords or two-step sign-in, and deactivate leavers.
  Deactivating also signs them out and revokes their Claude tokens.
- Logs: `docker compose logs -f cms` (security events: logger `crtdh.security`); agent: `state/logs/agent.log`
  on the campus PC.

## 4. The 10 most likely incidents

| # | Symptom | Likely cause | Fix |
|---|---|---|---|
| 1 | CMS shows "Waiting for upload machine (last seen …)" for a long time | campus PC off, asleep or off the network; task stopped | Switch it on and sign in; `python -m publish_agent status`; restart the scheduled task. The publish fails as "timeout" after `PUBLISH_STALE_UPLOAD_AFTER` (30 min); publish again |
| 2 | Agent log: `CMS refused the agent (401)` | `agent-secret.txt` ≠ `AGENT_HMAC_SECRET`, or the PC clock is off by more than 5 min | fix the secret; sync the clock (Windows: Settings → Time → Sync now) |
| 3 | Agent log: `cannot reach the CMS` or an HTML/302 response | lab server down, tunnel down, or the campus IP changed so the Access bypass no longer matches | `docker compose ps` on the server; re-check the campus IP (GO-LIVE 2.5) and update the Access bypass |
| 4 | Publish failed at a build step | build guard (missing list, or a collection shrank >30% without confirmation), a media file missing, frontend build error | The review screen shows the step and message. Fix the content, or confirm the shrink, and publish again. Build log: `/data/publish/builds/<publish id>/build.log` in the worker. The live site doesn't change |
| 5 | Publish failed at `check_live`, or "the site did not show the new build" | Apache or a proxy cache served old pages; the marker is missing | The agent has already rolled back. Check `.htaccess` is honoured, wait, and publish again. Compare `curl -s https://crtdh.iitkgp.ac.in/ \| grep crtdh-build` with `status` |
| 6 | Agent: `disk quota is probably full` | CIC quota | `check` shows free space; lower `keep_releases`; delete old `crtdh-releases/releases/legacy-*` only after confirming you have its backup |
| 7 | Agent: `host key CHANGED` | server reinstalled, or someone in the middle | **Stop.** Confirm with the CIC before trusting the new key; then `check --trust-host-key` and update the fingerprint in §1 |
| 8 | A staff member is locked out ("Sign-in is paused") or lost their phone | 5 wrong tries (lockout with backoff), or lost authenticator | wait for `locked_until`, or Admin → **Users** → Reset two-step sign-in (also signs them out) |
| 9 | Claude: can't connect, or 403 | WAF IP rule out of date with Anthropic's ranges; OAuth client secret rotated; the 30-day grant ended | update the WAF rule; re-add the connector with the current secret; the user clicks Connect again |
| 10 | Contact form shows the mailto link, or messages fail | lab server or tunnel down; `TURNSTILE_SECRET` wrong; CORS origin ≠ public site | `docker compose logs cms \| grep -i turnstile`; check `CORS_ALLOWED_ORIGINS=https://crtdh.iitkgp.ac.in`; the mailto fallback keeps enquiries flowing meanwhile |

Also check `cms` restart loops after any `.env` edit. The production checks refuse unsafe settings on purpose,
and the log line names the problem.

## 5. Sign-off checklist for the 31 Jan 2027 handover

Every account must belong to the **institute** (a role mailbox such as a centre address), not to Annjan
personally. Its 2FA and recovery codes go to the successor and the centre head.

**Accounts and ownership**

- [ ] Cloudflare account: owner email is an institute role mailbox; successor added as Super Administrator; Annjan removed or downgraded
- [ ] Domain `<domain>`: registrant is the institute; auto-renew on; renewal email is a role mailbox; registrar login in the password manager
- [ ] GitHub: repo transferred to an institute-owned organisation (or successor added as admin); repo visibility decided (public history contains the old fixture hash); Dependabot and CI secrets reviewed
- [ ] Email/SMTP used by `EMAIL_URL`: institute-owned
- [ ] Claude: the Team Owner (if a Team plan) is a staff member who stays; the connector's client secret is in the password manager
- [ ] AWS (old 5 Sep EC2): confirmed terminated; account closed or handed over
- [ ] Password manager vault (or sealed document) containing everything in §2, handed to the successor and the centre head

**Machines**

- [ ] Lab server: successor has an SSH account; Annjan's keys and account removed; location and power owner recorded
- [ ] Campus PC 10.111.26.20: successor can sign in; the agent task runs under an account that stays; the CIC password changed after handover
- [ ] Server facts table (§1) complete

**Rotation at handover** (everything Annjan saw)

- [ ] `SECRET_KEY`, `AGENT_HMAC_SECRET`, `CMS_INTERNAL_SECRET`, `POSTGRES_PASSWORD`, backup passphrase
- [ ] Claude OAuth client secret (`create_claude_client --rotate`)
- [ ] CIC account password; SFTP key if Annjan had a copy
- [ ] Annjan's CMS account deactivated (revokes his Claude tokens too)

**Knowledge**

- [ ] Successor ran one restore drill (§3) and one publish + rollback, with Annjan watching
- [ ] Successor read `deploy/README.md`, `publish_agent/README.md`, `docs/mcp.md`, this file
- [ ] Real-staff UAT signed off (`docs/uat/README.md`)
- [ ] Open items from GO-LIVE step 10 and the known gaps below have owners

Signed: outgoing ____________ incoming ____________ centre head ____________ date ________

## 6. Known gaps at the time of writing (19 Nov 2026)

- Production `worker` can't run the frontend build (no Node or frontend in the image; `/data/publish` not on a
  volume). See GO-LIVE blocker 1.
- The publish agent sends no Cloudflare Access headers, so it needs the path bypass (GO-LIVE 2.5).
- `docs/connect-claude.md` and `docs/mcp.md` say "CMS → your profile → Disconnect Claude". The admin app has no
  such screen yet (the user menu has only Sign out / Sign out on all devices). The API
  `POST /api/v1/cms/claude-access/revoke/` exists.
- With the real API, `GET /api/v1/cms/pages/` returns the site-wide sections under `globals`, not as a page with
  id `site`. So the admin's **Header & footer** nav entry (`AppShell.jsx`, which looks for `id === 'site'`) only
  appears with the mock. Staff can still reach those sections by clicking the header or footer on the canvas.
- `docs/privacy-notice.md` calls the retention job the `purge` service; in compose it is `housekeeping`.
  `deploy/.env.example` calls the agent config `config.toml`; it is `config.ini`.
- No uptime monitor or `make dev` in the repo. No sandbox page for first Claude tries (PLAN WS4.8).
- `cleartokens` isn't scheduled (see §3).
