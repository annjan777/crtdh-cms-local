# Deploying the CRTDH CMS zone (lab server)

The public website is static files on the CIC server (published by the campus publish agent). This
stack is the private CMS zone: Postgres, the Django CMS API (gunicorn), the MCP server (uvicorn), the
publish worker, a daily housekeeping job, an nginx gateway serving the admin SPA, and `cloudflared`.

Nothing publishes a host port. All traffic arrives through one Cloudflare Tunnel:

| Hostname | Goes to | Protection |
|---|---|---|
| `cms.<domain>` | gateway: admin SPA, `/api/`, `/oauth/authorize/` | Cloudflare Access (SSO) + CMS sign-in with TOTP |
| `mcp.<domain>` | mcp: only `/mcp`, OAuth metadata, `/oauth/token/`, `/oauth/revoke_token/` | WAF: source IP in `160.79.104.0/21` or `153.61.208.0/20` only + OAuth |
| `contact.<domain>` | gateway: only `POST /api/v1/contact/` | Turnstile, 5/min/IP in the app, WAF rate limit |

### Network

- `internal` (172.30.80.0/24, no internet) holds every container. The gateway (172.30.80.10) and
  cloudflared (172.30.80.11) have fixed addresses; the app processes (`cms`, `mcp`) accept requests only
  from those two (`REQUIRE_TRUSTED_PROXY`, `TRUSTED_PROXY_IPS`) and honour `CF-Connecting-IP` /
  `X-Forwarded-Proto` only from them. Not publishing ports does not stop a process on the server from
  reaching a container's bridge address directly; this check is what does. uvicorn runs with
  `--no-proxy-headers` so the peer stays cloudflared's address.
- `egress` (172.30.81.0/24, outbound only) is joined only by what must reach the internet: cloudflared
  (Cloudflare edge), `cms` (Turnstile siteverify, SMTP), `mcp` (`upload_image_from_url`, SSRF-guarded),
  `worker` (SMTP). `db`, `migrate`, `housekeeping` and `gateway` have no internet. If the lab requires
  it, restrict `egress` further on the host firewall to 443 and the SMTP port.
- If 172.30.80.0/24 or 172.30.81.0/24 clash with a lab network, change the subnets, the two
  `ipv4_address` values and `TRUSTED_PROXY_IPS` together.
- The gateway runs with a read-only root, all capabilities dropped except those nginx's master needs
  to bind :80 and switch to the `nginx` user, and serves Django's collected static files at `/static/`
  (the `migrate` job runs `collectstatic` into the `static_data` volume).

## 1. Configure

```bash
cd deploy
cp .env.example .env            # gitignored; fill every <...>
chmod 600 .env
```

- `SECRET_KEY` and `POSTGRES_PASSWORD`: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
- The CMS refuses to start if `SECRET_KEY` is missing, short or a known default, if `ALLOWED_HOSTS`
  contains `*`, if CORS allows all origins or any origin is not https, if `DATABASE_URL` is SQLite, or if
  `DJANGO_ADMIN_ENABLED` is set (config/security.py). Fix the message it prints; never weaken the check.
- `CLOUDFLARED_IMAGE`: pin a current release by digest (`docker pull cloudflare/cloudflared:<ver>`,
  then `docker inspect --format '{{index .RepoDigests 0}}'`).

## 2. Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create crtdh-cms          # writes <TUNNEL_ID>.json
cp ~/.cloudflared/<TUNNEL_ID>.json cloudflared/credentials.json && chmod 600 cloudflared/credentials.json
cp cloudflared/config.yml.template cloudflared/config.yml   # replace <TUNNEL_ID> and <domain>
cloudflared tunnel route dns crtdh-cms cms.<domain>
cloudflared tunnel route dns crtdh-cms mcp.<domain>
cloudflared tunnel route dns crtdh-cms contact.<domain>
```

Then, in the Cloudflare dashboard, do the four items listed at the top of `config.yml.template`
(Access app for `cms.`, WAF IP rule for `mcp.`, rate-limit rule for `contact.`, TLS settings).
The MCP hostname being outside Access is a deliberate, documented exception (PLAN WS4.2).

### Publish agent and Cloudflare Access

The campus publish agent calls `https://cms.<domain>/api/v1/agent/*` and can't do an Access sign-in. Give it an
Access **service token** (preferred over an IP bypass: campus egress IPs change and are shared):

1. Zero Trust → Access → Service auth → **Create service token**, name `crtdh-publish-agent`, duration 1 year (put
   the expiry date in the handover calendar). Copy the **Client ID** and **Client Secret** now; the secret is shown
   once.
2. Access → Applications → Add → Self-hosted: name `CRTDH publish agent`, domain `cms.<domain>`, path
   `api/v1/agent/`. Policy: Action **Service Auth**, Include **Service Token** = `crtdh-publish-agent`. Nothing
   else. Access uses the most specific path, so the rest of `cms.` keeps the SSO policy.
3. On the campus PC: in `config.ini` set `[cms] access_client_id = <Client ID>`, and put the Client Secret on one
   line in `access-secret.txt` next to `config.ini` with `access_secret_file = access-secret.txt` (or in the
   `CRTDH_CF_ACCESS_SECRET` environment variable). The agent refuses a secret written into `config.ini`, sends both
   as `CF-Access-Client-Id` / `CF-Access-Client-Secret` on every CMS request, and masks the secret in its logs.

The agent's HMAC signature still protects every endpoint behind the token. Check from the campus PC:
`python -m publish_agent check` reports `CMS connection : ok`; without the token the agent says "Cloudflare Access
sent the agent to its sign-in page". Rotate by creating a new token, updating `access-secret.txt`, then deleting
the old token.

## 3. Start

```bash
docker compose up -d --build
docker compose ps          # migrate should show "exited (0)"; everything else "running"
```

## 4. First admin (once)

```bash
docker compose run --rm cms python manage.py createsuperuser
```

Type the password at the prompt (never on the command line or in a file). On first sign-in at
`https://cms.<domain>` the CMS asks you to set up an authenticator app and shows 10 recovery codes
once. Create everyone else from the CMS user screen; each gets a one-time temporary password and
must enrol TOTP at first sign-in. There are no default accounts and no seed users in production.

To import the bundled content once into an empty database (never on a database that has edits):
`docker compose run --rm -e CRTDH_ALLOW_SEED=1 cms python manage.py bootstrap_local`
(it refuses any fixture that contains users).

## 5. Operations

- **Update**: `git pull && docker compose up -d --build` (migrations run in `migrate` first).
- **Logs**: `docker compose logs -f cms` (security events are on the `crtdh.security` logger).
- **Someone lost their phone**: an admin uses "Reset MFA" on the user; that also signs them out.
- **Someone leaves**: "Deactivate" signs them out everywhere and revokes their MCP tokens.
- **Rotate `SECRET_KEY`**: change it in `.env`, `docker compose up -d`. Everyone is signed out.
- **Backups**: the `pgdata` and `media_data` volumes are the only state. Back them up encrypted, e.g.
  `docker compose exec -T db pg_dump -U crtdh crtdh | gpg -c > crtdh-$(date +%F).sql.gpg` (`-T`: no TTY, or the dump is corrupted). Test a restore.
- **Contact messages** are deleted automatically after `CONTACT_RETENTION_DAYS` (default 365) by the
  `housekeeping` service (`docs/privacy-notice.md`).

## Local development

Use `docker-compose.local.yml` in the repo root (DEBUG on, seeded content, no users). Create local
test users with `python manage.py create_dev_users` (prints random passwords once; refuses with DEBUG off).
