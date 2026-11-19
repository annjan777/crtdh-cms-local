# CRTDH staging on the homelab

This kit runs the **real** production stack (`deploy/docker-compose.yml`, unchanged) on a home server under
Docker, and puts it on the internet through a Cloudflare tunnel, so it can be tested remotely before go-live.
A small stand-in replaces the institute's web server: an SFTP account plus Apache. The real publish agent
uploads to it, just as the campus PC will upload to the CIC server.

| URL | What | In production this is |
|---|---|---|
| https://crtdh.annjan.in | public website (Apache, files uploaded by the agent) | crtdh.iitkgp.ac.in (CIC server) |
| https://cms-crtdh.annjan.in | admin app + CMS API + OAuth sign-in | cms.&lt;domain&gt; |
| https://contact-crtdh.annjan.in | contact form relay (POST only) | contact.&lt;domain&gt; |
| https://mcp-crtdh.annjan.in | Claude connector (MCP) | mcp.&lt;domain&gt; |

Files: `docker-compose.staging.yml` (override), `setup.sh`, `smoke.sh`, `teardown.sh`, `dc.sh` (docker compose
with the right files), `TUNNEL.md` (Cloudflare dashboard steps), `sftp/`, `site/` and `agent/` (the stand-ins).
Everything secret goes into `deploy/staging/.env.staging` and `deploy/staging/secrets/`. Both are git-ignored.

## 10 steps

1. **Check the server.** Any 64-bit Mac or Linux box with 4 GB of memory free for Docker (6 GB is better) and
   20 GB of free disk. It must stay awake: turn off sleep.
2. **Install Docker.** Run `deploy/staging/setup.sh --dry-run`. If Docker is missing, it prints the exact install
   steps for this machine (Docker Desktop or Colima on macOS, Docker's apt repository on Ubuntu/Debian). You
   need Docker Compose 2.24.4 or newer. The dry run also writes a throw-away env file and keys into a temporary
   folder and shows them with the secrets masked.
3. **Get the code** on the server: clone the repository and check out the branch you were given (the release or
   staging branch). Run every command below from the repository folder.
4. **Create the tunnel** in the Cloudflare dashboard and copy its token: `TUNNEL.md` section 1.
5. **Add the six routes** (public hostnames): `TUNNEL.md` section 2. Bot Fight Mode off: section 3.
6. **Run setup**: `deploy/staging/setup.sh`. It:
   - checks Docker;
   - writes `.env.staging` with new random secrets and asks for the tunnel token (hidden input);
   - makes the SFTP keys and the agent's config;
   - builds and starts everything (the first build takes 10-20 minutes);
   - runs the migrations;
   - imports the bundled content (no user accounts);
   - asks you to create **your** admin account (you type the password; the script never sees it);
   - prints the Claude connector's client id and secret **once** (copy them into your password manager);
   - runs the publish agent's server check.

   Running it again is safe: it keeps the secrets and the data, and only fills in what's missing.
7. **Sign in** at https://cms-crtdh.annjan.in with that account (username and password; two-step sign-in is off
   unless `MFA_ENABLED=True` is set in `.env.staging`).
8. **Publish once.** Change one small thing (for example a news item), open **Review & publish** and press
   **Publish**. Watch it with `deploy/staging/dc.sh logs -f worker publish-agent`. The status goes queued →
   building → uploading → **Live**. Then https://crtdh.annjan.in shows the site.
9. **Run the smoke test** from any computer (it needs only bash and curl): `deploy/staging/smoke.sh`. Every line
   should say PASS. Send the output to whoever is testing.
10. **Optional extras**: restrict the MCP host to Anthropic's IP ranges (`TUNNEL.md` section 4), put Cloudflare
    Access in front of the CMS (section 5), or connect Claude: claude.ai → Customize → Connectors → Add custom
    connector, URL `https://mcp-crtdh.annjan.in/mcp`, and paste the client id and secret from step 6 under
    Advanced settings. When you're done: `deploy/staging/teardown.sh` stops everything and keeps the data;
    `teardown.sh -v` deletes the data as well.

## Everyday commands

| What | Command |
|---|---|
| Status | `deploy/staging/dc.sh ps` |
| Logs | `deploy/staging/dc.sh logs -f cms worker publish-agent cloudflared` |
| Emails (staging sends none; they're printed here) | `deploy/staging/dc.sh logs cms worker \| grep -A20 "Subject:"` |
| Update after `git pull` | `deploy/staging/setup.sh` (rebuilds, migrates, keeps data) |
| Agent: what's live | `deploy/staging/dc.sh exec publish-agent python -m publish_agent status` |
| Agent: previous release back | `deploy/staging/dc.sh stop publish-agent && deploy/staging/dc.sh run --rm --no-deps publish-agent rollback && deploy/staging/dc.sh start publish-agent` |
| Look at the "CIC server" files | `deploy/staging/dc.sh exec site ls -la /srv/www /srv/www/crtdh-releases/releases` |
| New Claude client secret | `deploy/staging/dc.sh exec cms python manage.py create_claude_client --rotate` |
| Someone forgot their password | another admin: CMS → Users → Reset password |

## How staging differs from production

| | Production | Staging (this kit) |
|---|---|---|
| Web server | CIC's Apache at academicweb.iitkgp.ac.in | `site`: Apache 2.4 with `AllowOverride FileInfo`, serving the `sftp` account's web root |
| Publish agent | campus PC, `config.ini` next to it | `publish-agent` container. Same code. It reaches the CMS through Cloudflare. Host key pinned by setup.sh |
| Tunnel | locally managed (`config.yml` + `credentials.json`) | remotely managed: token only, routes in the dashboard |
| Cloudflare Access on the CMS | yes | off by default; MFA protects sign-in (`TUNNEL.md` section 5 to turn it on) |
| Turnstile | real widget | Cloudflare's **test** keys (always pass). Labelled in `.env.staging` |
| Email | SMTP | none: printed in the logs (`EMAIL_URL=consolemail://`) |
| Users | real staff | only you. Don't put real staff accounts or private data on staging |

## If something goes wrong

- **`cms` keeps restarting**: `deploy/staging/dc.sh logs cms | tail -30`. The production check prints the
  setting it refuses. Fix `.env.staging` (or run `setup.sh` again).
- **A URL gives Cloudflare error 1033 or 502**: the tunnel is down or a route points at the wrong service. Check
  `dc.sh logs cloudflared` and the table in `TUNNEL.md` section 2.
- **Publish stuck at "waiting for upload machine"**: `dc.sh logs publish-agent`. A 401 means the agent secret
  doesn't match (run `setup.sh` again; it rewrites `agent-secret.txt` from `.env.staging`). A 403 or a Cloudflare
  challenge page means Bot Fight Mode or Access is in the way (`TUNNEL.md` sections 3 and 5).
- **"the site did not show the new build"**: the agent rolled back on its own. Check that
  https://crtdh.annjan.in/ reaches the `site` container (route 1).
- **The address pool 172.30.80.0/24 or 172.30.81.0/24 clashes with your home network**: change both subnets,
  the two fixed addresses and `TRUSTED_PROXY_IPS` together, as `deploy/README.md` "Network" describes. Keep each
  `ip_range` inside its subnet and the fixed addresses outside it.
