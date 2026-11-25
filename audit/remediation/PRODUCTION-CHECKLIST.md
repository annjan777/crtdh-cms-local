# Production checklist: CRTDH CMS v3

Updated 2026-11-20 with the owner's decisions. Steps for the owner (Annjan) and CIC; nothing here has been done yet.
Release candidate: branch `v3/remediation`. Production = lab server (CMS, MCP, worker) + CIC Apache (public site).

## Owner decisions (risk accepted, recorded)
| Item | Decision | What it means |
|---|---|---|
| MFA (F-01) | **Off** | One password controls publishing and Claude access. Use a long, unique password per admin (16+ characters, password manager) and keep the number of Admins small. |
| CIC SFTP password emailed to 7 people (F-02) | **Left as is** | Anyone with that email can overwrite the live site directly. Revisit if staff change. |
| Uptime alerts (R-13) | **None** | Outages are noticed by people. |
| Backups (F-03) | **CMS Backup page only** | No scheduled server backup. An Admin downloads backups and keeps them off the server. |
| Privacy contact (R-5) | **Left out for now** | The notice is published without the "write to …" sentence. |

## 1. Tomorrow on the production server (with access + old site files)
- [ ] `git fetch crtdh-v3-remediation.bundle v3/remediation:v3/remediation` (or pull after pushing), check out the branch.
- [ ] `deploy/.env` from `deploy/.env.example`: fresh `SECRET_KEY`, DB password and `AGENT_HMAC_SECRET` (never staging's),
      `CRTDH_ENV=production`, real `TURNSTILE_SITE_KEY`/`TURNSTILE_SECRET`, `MFA_ENABLED=False` (decision above), and no
      `CRTDH_ALLOW_TEST_SEED`.
- [ ] Old site files: before the first publish, list the CIC web root with CIC. Keep what is needed, and leave nothing like `.git/`, `.env`,
      `*.bak`, `*.sql`, `phpinfo.php` or old CMS installs. The publish agent backs up the existing site as `legacy-*` outside
      `public_html` (`python -m publish_agent backup` on the campus PC; copy that file off the PC).
- [ ] `docker compose up -d`; `docker compose ps` all healthy; `docker compose exec gateway nginx -t` (new gateway rules).
- [ ] Find out whether Cloudflare is in front of `crtdh.iitkgp.ac.in` (`dig +short crtdh.iitkgp.ac.in`: Cloudflare IPs?). If yes:
      turn off Email Address Obfuscation and Web Analytics for that zone.
- [ ] First publish from the CMS, then the checks in §2.

## 2. Verify (each needs output or a screenshot)
- [ ] `/contact/#privacy` shows "How we use your message"; the footer shows "How we use contact messages".
- [ ] Map and videos show "Show the map" / "Watch" and load only after the click.
- [ ] `python3 tests/tools/check_headers.py --site https://<site>`: 0 FAIL (CIC must honour the `.htaccess`).
- [ ] `curl -s https://<site>/_media/`: no file listing. `/does-not-exist/` gives a 404 page.
- [ ] `python3 tests/tools/check_headers.py --cms https://<cms>`: 0 FAIL. `https://<cms>/.env` returns 404.
- [ ] Lab server: `sudo ss -ltnp` shows nothing public except SSH (and the gateway if no tunnel). Firewall default-deny inbound.
- [ ] One real contact message arrives (real Turnstile keys).
- [ ] **Backup page**: download *content + photos* once and store it off the server. If it is over 100 MB and the CMS is behind
      Cloudflare, uploading it back needs the campus network.

## 3. Credentials (needed even with the decisions above)
- [ ] Claude client secret (it was pasted in chat on 19 Nov): CMS → Claude access → **Create a new client secret**, then
      **Disconnect** existing connections. Put the new secret in claude.ai's connector settings. The old secret must then fail.
- [ ] Every admin password: 16+ characters, unique, from the password manager (no MFA, so this is the only lock).

## 4. Content (any Admin, in the CMS)
- [ ] Media → Media coverage: `http://pib.nic.in/…` → `https://`; check the uniindia link opens over https before changing it.
- [ ] Re-export the 8192 px "Jio" gallery photo at about 2400 px.

## 5. Sign-off
| Item | Evidence | Date |
|---|---|---|
| Release-commit test suites green (TEST-RESULTS.md) | | |
| Production `.env` checked, no test seeding | | |
| Old site files reviewed with CIC | | |
| §2 checks done | | |
| Claude secret rotated, admin passwords strong | | |
| First full backup downloaded and stored off the server | | |
| Owner go/no-go (Annjan) | | |
