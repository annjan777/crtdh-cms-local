# GO-LIVE runbook: from zero to a live CRTDH v3 site

Who this is for: the person deploying (Annjan). Do the steps in order. Each step lists the commands, what you
should see, how to check it, and how to undo it. Tick the boxes as you go and paste real outputs into the
"Record" lines. Those records become the server facts the successor needs (see [HANDOVER.md](HANDOVER.md)).

Placeholders: `<domain>` is the Cloudflare-managed domain that will hold `cms.` and `contact.`
(see step 2.1). The public site stays at `https://crtdh.iitkgp.ac.in/` on the CIC server
`academicweb.iitkgp.ac.in`.

> **Read first: blockers found while writing this runbook** (19 Nov 2026). Until they are fixed in code, the steps marked BLOCKED below will fail.
>
> 1. **Fixed (publish worker).** The `worker` now has its own image (`deploy/worker/Dockerfile`: the backend plus
>    Node 22 and `frontend/` with its build dependencies), runs non-root on a read-only root file system, and keeps its
>    work on the named volume `publish_data` (`/data/publish`; the `cms` mounts it read-only to serve tarballs). The
>    build command and output folder are set in `docker-compose.yml`, not in `.env`. Not yet built under Docker
>    (see item 3): if step 6 fails, check `docker compose logs worker` first.
> 2. **Fixed (publish agent vs Cloudflare Access).** The agent now sends a Cloudflare Access service token
>    (`CF-Access-Client-Id` / `CF-Access-Client-Secret`). Step 2.5 creates the token and an Access policy for
>    `/api/v1/agent/` that allows only that token; step 5.3 puts it in the agent's config.
> 3. **Nothing in `deploy/` has been run under Docker yet.** The sandbox had no Docker daemon (`docs/testing.md`).
>    The production settings were tested in the rehearsal instead. Expect to fix small issues on the day, and keep
>    this runbook open to note them.

---

## 0. URGENT, before anything else (about 30 min)

These fix exposures that already exist. They don't depend on the new system.

### 0.1 Check the old 5 Sep EC2 deployment and take it down

That deployment came from this repo before WS0. It probably runs `bootstrap_local` on every start, and the seed
then contained superuser `admin` / `adminpassword`.

1. Sign in to the AWS console (the account the 5 Sep deployment used). Go to EC2 → Instances, in every region you
   might have used.
2. For each running CRTDH instance, check from your laptop:
   ```bash
   curl -sI http://<ec2-public-ip-or-dns>/admin/ | head -3
   curl -sI http://<ec2-public-ip-or-dns>:8000/admin/ | head -3
   ```
   If either returns `200` or `302`, the old Django admin is reachable.
3. **Stop** the instance (Instance state → Stop). If you don't need its data, **Terminate** it. Also delete its
   security-group rules that open 80/443/8000, and release any Elastic IP.
4. Record: `EC2 instance id ____ region ____ stopped/terminated at ____`.

Verify: the `curl` commands above time out or are refused.
Roll back: none needed. If someone relied on that copy, they move to the new CMS.

### 0.2 Never reuse `admin` / `adminpassword`

- Production has **no** default or seed users. The current `local_seed.json` has no `auth.user` rows, and
  `bootstrap_local` refuses fixtures that contain users. You create the first admin by hand in step 4.4.
- The old password hash is still in **git history**, and the repo `annjan777/crtdh-cms-local` is public. Decide
  today: make the repo private (GitHub → Settings → General → Danger Zone → Change visibility), or purge the
  fixture from history (`git filter-repo`). Either way, treat `adminpassword` as known to everyone. Never use the
  user name `admin` with that password anywhere.
- Record: `repo made private / history purged on ____ by ____`.

### 0.3 Change the CIC server password that was emailed to 7 people

Do this from the whitelisted campus PC (10.111.26.20). It is the only machine allowed to reach the server.

```bash
ssh <USER>@academicweb.iitkgp.ac.in
passwd            # type the old password once, then the new one twice
exit
```

You should see `passwd: password updated successfully` (wording varies by OS). If you see
`passwd: Authentication token manipulation error` or `This account is currently not available`, the account
can't change its own password. Write that down, and set up the SSH key in step 5.2 instead.

- Store the new password in a password manager only. Don't email it or put it in any file on the PC.
- Record: `passwd allowed: yes/no` (this is part of the WS0.7 server discovery).

Verify: `ssh <USER>@academicweb.iitkgp.ac.in` with the old password fails.
Roll back: run `passwd` again. If you lock yourself out, the CIC can reset it (they issued the credentials).

### 0.4 Never commit secrets

- Real values go only in `deploy/.env`, `deploy/cloudflared/config.yml` and `deploy/cloudflared/credentials.json`
  on the lab server. They are all in `.gitignore`. Never `git add -f` them.
- The publish agent's secret goes only in `agent-secret.txt` on the campus PC. Its config refuses passwords and
  secrets.
- Before every push, check:
  ```bash
  git status --short deploy/            # must not list .env, config.yml or credentials.json
  git diff --cached | grep -nE 'SECRET|PASSWORD|BEGIN .*PRIVATE KEY' || echo clean
  ```
- CI runs gitleaks on every push (`.github/workflows/ci.yml`).

### 0.5 Push the release code

The v3 work lives on local branches. The lab server needs to clone it. Merge the final integration branch into
`main` and push it to GitHub (or to the institute-owned repo, see HANDOVER sign-off). Record the commit you
deploy: `release commit ____`.

---

## 1. Prepare the lab server (about 45 min)

**Unknown:** the lab server's OS, CPU and disk haven't been recorded yet. Run these and record the output:

```bash
cat /etc/os-release | head -4
uname -m
nproc; free -h; df -h /
```

Needs: 64-bit Linux, 2+ CPU cores, 4 GB RAM (the frontend build runs on it), 20 GB free disk (Postgres, media,
build tarballs). The image alone ships about 215 MB of seed media.

### 1.1 Install Docker Engine and the Compose plugin

Follow the official guide for your distribution: docs.docker.com/engine/install/. Use the apt or dnf repository
method, not a convenience script. Then:

```bash
sudo usermod -aG docker $USER      # sign out and back in afterwards
docker version --format '{{.Server.Version}}'
docker compose version
```

Expect Docker 24 or newer and `Docker Compose version v2.x`. `deploy/docker-compose.yml` uses `name:` and
`service_completed_successfully`, so Compose v1 (`docker-compose`) won't work.

Also install `git`, `gpg` and `cloudflared` (Cloudflare's packages: developers.cloudflare.com → Cloudflare Tunnel →
Downloads). Check with `cloudflared --version`.

### 1.2 Firewall: no inbound ports

Every request reaches the CMS through the Cloudflare Tunnel, which is an *outbound* connection from the server.
The compose file publishes no host port. Only SSH from the lab network needs to come in.

On Ubuntu/Debian with `ufw` (adapt for `firewalld` on RHEL-family systems):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <lab LAN CIDR, e.g. 10.x.x.0/24> to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

Expect `Default: deny (incoming), allow (outgoing)` and a single port-22 rule.

Note: Docker writes its own iptables rules for *published* ports, and ufw doesn't see them. That doesn't matter
here because nothing is published. Keep it that way: never add `ports:` to `deploy/docker-compose.yml`.

Verify after step 4: from another lab machine, `nc -zv <server-ip> 80 443 8000 8400` gets "refused" or a timeout
for each port.
Roll back: `sudo ufw disable`.

### 1.3 Get the code

```bash
sudo mkdir -p /srv/crtdh && sudo chown $USER /srv/crtdh
git clone https://github.com/annjan777/crtdh-cms-local /srv/crtdh/app
cd /srv/crtdh/app && git checkout <release commit> && git log --oneline -1
```

Record: `server OS ____, Docker ____, path /srv/crtdh/app, commit ____`.

---

## 2. Cloudflare: account, tunnel, DNS, Access, rate limit (about 60 min)

### 2.1 Account and domain

- **Unknown, decide first:** which domain holds the CMS hostnames. It must be a zone whose DNS is managed by
  Cloudflare. `iitkgp.ac.in` is the institute's and almost certainly can't be moved. Use a domain the lab owns,
  ideally registered in the **institute's** name and email (see HANDOVER sign-off). Record: `<domain> = ____`.
- Create the Cloudflare account with a **role mailbox** (for example a lab or centre address), not a personal
  one. Turn on 2FA for it. Add the domain (Free plan is enough). At the registrar, switch the nameservers to the
  two Cloudflare gives you, then wait until the zone shows **Active**.
- SSL/TLS → Overview: mode **Full**. Edge Certificates: **Always Use HTTPS** on, **Minimum TLS Version 1.2**.

### 2.2 Create the tunnel (on the lab server)

```bash
cd /srv/crtdh/app/deploy
cloudflared tunnel login                     # opens a URL; choose <domain>; writes ~/.cloudflared/cert.pem
cloudflared tunnel create crtdh-cms          # prints "Created tunnel crtdh-cms with id <TUNNEL_ID>"
cp ~/.cloudflared/<TUNNEL_ID>.json cloudflared/credentials.json && chmod 600 cloudflared/credentials.json
cp cloudflared/config.yml.template cloudflared/config.yml
sed -i "s/<TUNNEL_ID>/<the id>/; s/<domain>/<your domain>/g" cloudflared/config.yml
grep -n '<' cloudflared/config.yml || echo "all placeholders replaced"
```

The container reads the credentials file as user `nonroot`. If it can't read the `600` file, run
`sudo chown 65532:65532 cloudflared/credentials.json` (65532 is the usual user id of `nonroot` in the
cloudflared image; check with `docker inspect --format '{{.Config.User}}' <CLOUDFLARED_IMAGE>`).

### 2.3 DNS for the two hostnames

```bash
cloudflared tunnel route dns crtdh-cms cms.<domain>
cloudflared tunnel route dns crtdh-cms contact.<domain>
```

Each one prints `Added CNAME cms.<domain> which will route to this tunnel`. In DNS → Records you now see two
proxied (orange-cloud) CNAMEs to `<TUNNEL_ID>.cfargotunnel.com`.

What each hostname serves is defined in `cloudflared/config.yml` and `nginx/templates/gateway.conf.template`:

| Hostname | Serves | Protection |
|---|---|---|
| `cms.<domain>` | admin app, `/api/` | Cloudflare Access + CMS password |
| `contact.<domain>` | only `POST /api/v1/contact/` | Turnstile + 5/min/IP in the app + WAF rate limit |

### 2.4 Cloudflare Access for `cms.`

Zero Trust dashboard → Access → Applications → **Add an application** → Self-hosted.

- Name `CRTDH CMS`, domain `cms.<domain>`, path empty (the whole host). Session duration 24 h.
- Policy `Lab staff`: Action **Allow**, Include **Emails** = each staff member's address (or **Emails ending in**
  the institute domain if every member has one).
- Login method: **One-time PIN** works with no other identity provider. Add Google or Microsoft later if the
  institute wants it.

Verify (after step 4): open `https://cms.<domain>` in a private window. You get the Cloudflare Access email-code
page first, then the CMS sign-in.

### 2.5 Access service token for the publish agent (required)

The agent on the campus PC can't do an Access sign-in, so it uses a service token. Full steps: `deploy/README.md`
→ "Publish agent and Cloudflare Access". In short:

1. Zero Trust → Access → Service auth → **Create service token** `crtdh-publish-agent` (1 year). Record the
   **Client ID** here and keep the **Client Secret** for step 5.3 (shown once; don't paste it anywhere else).
   Record: `token expires on ____` (add it to the handover calendar).
2. Access → Applications → Add → Self-hosted: name `CRTDH publish agent`, domain `cms.<domain>`, path
   `api/v1/agent/`. Policy: Action **Service Auth**, Include **Service Token** = `crtdh-publish-agent`, nothing else.

Verify: from any machine, `curl -s -o /dev/null -w '%{http_code}\n' https://cms.<domain>/api/v1/agent/next/`
returns `302` or `403` from Access (no token). With the token,
`curl -s -o /dev/null -w '%{http_code}\n' -H "CF-Access-Client-Id: <id>" -H "CF-Access-Client-Secret: <secret>" https://cms.<domain>/api/v1/agent/next/`
returns `401` from the CMS (unsigned request). Clear your shell history afterwards if you typed the secret.

### 2.6 Rate limit for `contact.`

Security → WAF → Rate limiting rules → Create: if `http.host eq "contact.<domain>"`, count by IP, block.
The template suggests 10 requests a minute. On the Free plan the counting period may be fixed at 10 seconds; if
so, use about 3 requests per 10 seconds. The app enforces 5 a minute per IP on its own.

Roll back for all of step 2: delete the Access apps, rules and DNS records, then `cloudflared tunnel delete crtdh-cms`.

---

## 3. Secrets and `deploy/.env` (about 20 min)

```bash
cd /srv/crtdh/app/deploy
cp .env.example .env && chmod 600 .env
gen() { python3 -c "import secrets; print(secrets.token_urlsafe(64))"; }
```

Fill **every** `<...>` value. Here is where each one comes from:

| Variable | Value / how to generate |
|---|---|
| `CMS_HOST`, `CONTACT_HOST` | `cms.<domain>`, `contact.<domain>` (no scheme) |
| `PUBLIC_SITE_URL`, `SITE_URL` | `https://crtdh.iitkgp.ac.in` |
| `POSTGRES_PASSWORD` | `gen` (avoid characters that need URL-escaping in `DATABASE_URL`; `token_urlsafe` is safe) |
| `DATABASE_URL` | `postgres://crtdh:<POSTGRES_PASSWORD>@db:5432/crtdh` |
| `SECRET_KEY` | `gen` |
| `ALLOWED_HOSTS` | `cms.<domain>,contact.<domain>` |
| `CSRF_TRUSTED_ORIGINS`, `CMS_PUBLIC_URL` | `https://cms.<domain>` |
| `CORS_ALLOWED_ORIGINS` | `https://crtdh.iitkgp.ac.in` (the public site calls the contact endpoint) |
| `TURNSTILE_SECRET`, `TURNSTILE_SITE_KEY` | from step 7.1 (fill in now or come back) |
| `CONTACT_NOTIFY_EMAIL` | role mailbox that receives "new message" alerts |
| `DEFAULT_FROM_EMAIL`, `EMAIL_URL` | **Unknown:** which SMTP service the lab may use. Ask the institute's mail admin. Format `smtp+tls://user:password@host:587` (URL-escape `@` in the password as `%40`) |
| `AGENT_HMAC_SECRET` | `gen`. Pasted again into the campus PC's `agent-secret.txt` in step 5.3 |
| `CMS_INTERNAL_SECRET` | `gen`, or leave empty to turn it off |
| `PUBLISH_ROOT`, `FRONTEND_BUILD_CMD`, `FRONTEND_BUILD_OUTPUT` | not in `.env` any more: `docker-compose.yml` and the worker image set them. Delete them from an older `.env` |
| `CONTACT_API_URL` | `https://contact.<domain>/api/v1/contact/` |
| `CLOUDFLARED_IMAGE` | `docker pull cloudflare/cloudflared:<current version>` then `docker inspect --format '{{index .RepoDigests 0}}' cloudflare/cloudflared:<version>` → paste the `cloudflare/cloudflared@sha256:...` value |

Check that nothing is left:

```bash
grep -nE '^[A-Z_]+=<' .env || echo "no placeholders left"
```

Store a copy of `.env` in the lab's password manager (as a secure note), so a dead disk is not a lost secret.

Never set these in production (the settings refuse some, the rest are test-only): `DEBUG=True`,
`CORS_ALLOW_ALL_ORIGINS`, `DJANGO_ADMIN_ENABLED`, `ALLOW_SQLITE`, `CRTDH_ALLOW_TEST_SEED`, `CRTDH_TEST_PASSWORD`,
`FAKE_BUILD_FAIL`.

---

## 4. Start the stack, first admin, MFA (about 30 min)

### 4.1 Start

```bash
cd /srv/crtdh/app/deploy
docker compose up -d --build          # first build: several minutes
docker compose ps
```

Expect `migrate` to show `exited (0)`, and `db`, `cms`, `worker`, `housekeeping`, `gateway` and
`cloudflared` to show `running`. `migrate` runs `migrate`, `createcachetable` and `collectstatic`; you don't run
them by hand.

If `cms` keeps restarting, run `docker compose logs cms | tail -30`. The production check (`config/security.py`)
prints exactly which setting it refuses (short or default `SECRET_KEY`, `*` in `ALLOWED_HOSTS`, a non-https CORS
origin, SQLite, `DJANGO_ADMIN_ENABLED`). Fix `.env`; never weaken the check.

```bash
docker compose logs cloudflared | grep -i "Registered tunnel connection"    # expect 4 lines
docker compose run --rm cms python manage.py check --deploy
```

`check --deploy` should report only `W021` (HSTS preload, left off on purpose). That's the rehearsal result in
`docs/testing.md`.

### 4.2 Import the current content (once, into the empty database only)

```bash
docker compose run --rm -e CRTDH_ALLOW_SEED=1 cms python manage.py bootstrap_local
docker compose run --rm cms python manage.py create_baseline_snapshot
```

`bootstrap_local` copies the bundled `seed_media/` into the media volume and loads `local_seed.json`. It refuses
fixtures that contain users. `create_baseline_snapshot` records this content as "what's live now", so the review
screen only shows real edits and *Discard* has something to go back to. It prints `baseline <id>: <collection>
<count>, ...`.

**Never run `bootstrap_local` again** on this database: it overwrites edits.

### 4.3 Create the first admin

```bash
docker compose run --rm cms python manage.py createsuperuser
```

Type the user name, email and password at the prompts. Never put the password on the command line or in a file.
Use your own name (for example `annjan`), **not** `admin`. A superuser counts as the Admin role
(`apps/accounts/roles.py`).

### 4.4 First sign-in and MFA

1. Open `https://cms.<domain>`, pass the Access email code, and sign in.
2. The CMS shows **Set up two-step sign-in**. Scan the QR code with an authenticator app (Google Authenticator,
   Microsoft Authenticator, 1Password …), then enter the 6-digit code.
3. **Save your recovery codes**: 10 codes, shown once. Put them in the password manager.
4. Go to **Users** → **Add a user** for each staff member, with role Editor, Publisher or Admin. Each person gets a
   one-time temporary password. They must change it and set up two-step sign-in at first sign-in. Send the
   temporary password through a separate channel from the CMS address (for example tell them in person or by
   phone).

Verify: sign out, sign in again. A password alone never opens the CMS; it always asks for the code.
Roll back for step 4: `docker compose down` stops everything and keeps the data. `docker compose down -v`
**deletes the database and media volumes**. Use it only if you want to start this step again from nothing.

---

## 5. Campus PC: publish agent, server discovery, backup (about 45 min)

Follow `publish_agent/README.md`. This is the short version, with what to record.

### 5.1 Install

On 10.111.26.20, install Python 3.10+, copy the `publish_agent` folder to `C:\crtdh-agent\publish_agent`
(Linux `/opt/crtdh-agent/publish_agent`), and from the parent folder run:

- Windows: `powershell -ExecutionPolicy Bypass -File publish_agent\install\setup.ps1`
- Linux/macOS: `sh publish_agent/install/setup.sh`

It creates `.venv`, `config.ini`, the key `keys/crtdh_publish_ed25519` and an empty `agent-secret.txt`. It
prints the public key line (`ssh-ed25519 ...`).

### 5.2 Key on the server

Sign in once with the (new) password and append the public key line to `~/.ssh/authorized_keys`
(`chmod 700 ~/.ssh`, `chmod 600 ~/.ssh/authorized_keys`). Record: `authorized_keys allowed: yes/no`.
If keys are refused, use the keyring password option ("Password instead of a key" in the agent README).

### 5.3 Configure and discover the server (this is WS0.7)

- Paste `AGENT_HMAC_SECRET` from `deploy/.env` into `agent-secret.txt` (one line).
- In `config.ini`, set `[sftp] user = <USER>` and `[cms] url = https://cms.<domain>`.
- Access token from step 2.5: set `[cms] access_client_id = <Client ID>` and `access_secret_file = access-secret.txt`,
  and put the Client Secret on one line in `access-secret.txt` next to `config.ini`.
- Run (Windows `.\.venv\Scripts\python.exe`, Linux `.venv/bin/python`):

  ```
  python -m publish_agent check --trust-host-key
  ```

Expect the server fingerprint, then a report that includes `Web root`, `Symlinks allowed`,
`.htaccess honoured`, `Free space (KB)`, `RECOMMENDED STRATEGY` and `CMS connection : ok (agent secret accepted)`.

- If the `Web root` is wrong, set `web_root` to one of the listed "Other web-root folders" and run it again.
- If `CMS connection` says "Cloudflare Access sent the agent to its sign-in page" or `403`, the service token or
  its Access policy (step 2.5) is missing or wrong.
- File permissions: the agent sets every file it uploads to `0644` and every folder to `0755` itself, so the
  site is readable by the web server whatever umask the account's SFTP server uses. If the agent log ever says
  "the server refused to set file permissions", the host doesn't allow `chmod` over SFTP. Then the uploaded files
  keep the server's default permissions. Check with `curl -sI https://crtdh.iitkgp.ac.in/` after the first publish:
  a `403` means the files aren't readable, so ask the CIC to set the SFTP umask to `022`.
- **Paste the whole report into HANDOVER.md → "Server facts"**, including the fingerprint. Also run
  `ssh <USER>@academicweb.iitkgp.ac.in 'sh -s' < publish_agent/discover.sh` if SSH commands are allowed (PHP or
  Python on the server, quota).
- Check that the live site is served over HTTPS: `curl -sI https://crtdh.iitkgp.ac.in/ | head -1`. Record the result.
- Institute web rules (GIGW, a central template) are a question for the centre head, not the CIC. Record the answer.

### 5.4 Back up the current live site

```
python -m publish_agent backup
```

Expect `backup saved: state/backups/live-site-before-agent-<time>.tar.gz`. Copy this file off the PC as well
(the lab drive and the password-manager vault are both fine). The agent also takes this backup before its first
publish, and moves the old site to `releases/legacy-<time>` (symlink or swap strategies), so `rollback --to
legacy-…` can bring it back.

### 5.5 Dry run, then run all the time

```
python -m publish_agent --dry-run run --once
```

Then install the always-on task from `publish_agent/install/` (Windows Task Scheduler `windows-task.xml`, Linux
`crtdh-publish-agent.service` with `User=` set, macOS plist). Check with `python -m publish_agent status`.
The CMS shows "Waiting for upload machine (last seen …)" whenever this PC is off.

---

## 6. First publish of the current content, and live check

1. In the CMS, make one small, real, harmless change (for example fix one item from `docs/content-gaps.md`). The
   draft bar shows **1 unpublished change on 1 page**.
2. **Review & publish** → **Publish 1 change**. The state moves through queued → building → "Publishing · waiting
   for upload machine" → uploading → **Live at HH:MM**.
   - If it fails at `snapshot` or `frontend`, read `docker compose logs worker` and the build log in the
     `publish_data` volume (`builds/<publish id>/build.log`).
3. Check the site is really live with this build:

   ```bash
   curl -s https://crtdh.iitkgp.ac.in/ | grep -o '<meta name="crtdh-build"[^>]*>'
   ```

   Its `content` must equal the snapshot id the agent reported (`python -m publish_agent status` → `server`).
   The agent checks this itself and rolls back automatically if the marker doesn't appear after 5 tries.
4. Open all 12 pages in a browser at phone and desktop width. Compare them with the old site (the golden
   regression test checks headings, items and images, but look anyway).
5. Check the old site's addresses now lead to the new pages (bookmarks and Google results still use them):

   ```bash
   curl -sI https://crtdh.iitkgp.ac.in/about.html | grep -iE '^(HTTP|location)'
   ```

   Expect `301` and `location: https://crtdh.iitkgp.ac.in/about/`. If it is `200` or `404`, CIC Apache is
   ignoring `.htaccess` redirects (mod_alias off or AllowOverride None); ask CIC to allow `FileInfo`.

Roll back: `python -m publish_agent rollback` (previous release) or `rollback --to legacy-…` (the site from
before the agent; the id is shown in `status`). For a broken CMS, use the manual upload runbook in
`publish_agent/README.md`.

---

## 7. Contact form and Turnstile (about 20 min)

### 7.1 Create the Turnstile widget

Cloudflare dashboard → Turnstile → Add widget. Hostname: `crtdh.iitkgp.ac.in`. Mode: Managed.

- Put the **site key** in `TURNSTILE_SITE_KEY`. It's public, and the frontend build bakes it in.
- Put the **secret key** in `TURNSTILE_SECRET`. Without it, production rejects every message on purpose.

Then run `docker compose up -d` (restarts with the new env), and publish once so the site carries the site key.

### 7.2 Check it

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://contact.<domain>/api/v1/contact/              # 403 (GET refused)
curl -s -o /dev/null -w '%{http_code}\n' https://contact.<domain>/anything                      # 404
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
  -d '{}' https://contact.<domain>/api/v1/contact/                                              # 400 (no Turnstile)
```

Then send a real message from the Contact page. Check that the alert arrives at `CONTACT_NOTIFY_EMAIL` (it holds
only the message id), and that the message appears in the CMS under **Messages** (Publisher/Admin only).
If the contact endpoint is down, the form shows a `mailto:` link instead.

Before launch, the privacy notice placeholders must be filled (see step 9).

---

## 8. Post-launch checks and rollback

Run these on launch day and after every deploy.

| Check | Command | Expect |
|---|---|---|
| Public headers | `python tests/tools/check_headers.py --site https://crtdh.iitkgp.ac.in` (from the repo, backend venv) | 0 FAIL. If Apache ignores `.htaccess`, the CSP/HSTS checks fail: record it and ask the CIC |
| Build marker | `curl -s https://crtdh.iitkgp.ac.in/ \| grep -o 'crtdh-build[^>]*'` | current snapshot id |
| 404 page | `curl -s -o /dev/null -w '%{http_code}' https://crtdh.iitkgp.ac.in/no-such-page/` | `404`, and the designed 404 page in a browser |
| Sitemap / robots | `curl -s https://crtdh.iitkgp.ac.in/sitemap.xml \| grep -c '<loc>'` and `curl -s https://crtdh.iitkgp.ac.in/robots.txt` | 12 URLs (one per page); robots names the sitemap |
| No CMS on the public host | `curl -s -o /dev/null -w '%{http_code}' https://crtdh.iitkgp.ac.in/api/v1/` | `404` |
| CMS gated | `curl -s -o /dev/null -w '%{http_code}' https://cms.<domain>/` | `302` (to Access) |
| Stack healthy | `docker compose ps` | all running, `migrate` exited (0) |

**Uptime check (to set up):** nothing in the repo checks uptime. Add an external HTTP monitor on
`https://crtdh.iitkgp.ac.in/` (keyword `crtdh-build`) and on `https://contact.<domain>/anything` (expects 404,
which proves the tunnel is up). Any free monitoring service works. Send the alerts to the lab role mailbox,
not a personal one.

**Rollback procedure:**

| What broke | Do |
|---|---|
| The last publish looks wrong | Campus PC: `python -m publish_agent rollback` (previous release), or `rollback --to <id>` |
| Go back to the pre-v3 site | `python -m publish_agent rollback --to legacy-…` (id from `status`) |
| Content is wrong in the CMS | Publisher: **Publish history** → **Restore** a version (it comes back as unpublished changes) → publish |
| A deploy broke the CMS | Lab server: `git checkout <previous commit> && docker compose up -d --build`. Migrations only move forward, so back up first (HANDOVER "Backups") |
| The CMS is down and the site must change | manual upload runbook, `publish_agent/README.md` |

---

## 9. What needs a human before launch

| Item | Who | Where |
|---|---|---|
| At least 12 photos of 2400 px or more (hero, building, labs, devices in use, camps, team). Hero uploads under 1600 px are refused | centre / photographer | `docs/content-gaps.md` → Photography; CMS **Photo shot list** |
| Text gaps: hero headline wording, proof figures with sources, PI's message, team designations, service and product descriptions, event dates, press headlines, nav labels | content owner | `docs/content-gaps.md` → Text |
| Is the personal Gmail in the footer meant to be public? | centre head | `docs/content-gaps.md` → Contact |
| Privacy notice: contact name/role and email, publication date, legal answers Q-01–Q-04 | centre head + institute legal | `docs/privacy-notice.md` |
| Institute web rules (GIGW, central template)? | centre head | record in HANDOVER |
| Real-staff UAT: one real run each of the editor and publisher sheets, no open **must** fail | staff + observer | `docs/uat/README.md` sign-off table |
| SMTP provider for alerts | institute mail admin | step 3 |
| Successor named, and institute-owned accounts | centre head | [HANDOVER.md](HANDOVER.md) sign-off |

Launch when blockers 1–2 are closed, steps 0–7 and 9 pass, and the table above has an owner and a date for every
row.
