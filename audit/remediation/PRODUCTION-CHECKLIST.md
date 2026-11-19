# Production checklist: CRTDH CMS v3

For the owner (Annjan) and CIC. Nothing here has been done by the remediation work: every step is yours or
CIC's to run, in this order. Tick a box only with the evidence it asks for.

Release candidate: branch `v3/remediation` (from `1f29d21`). Production = lab server (CMS, MCP, worker) + CIC
Apache (public site). The homelab is staging only and proves nothing about production.

---

## 0. Before anything: get the code onto the servers
- [ ] Review the branch (`audit/remediation/CODE-CHANGES.md`); push it when you approve.
- [ ] Staging first: on the homelab, `git pull` the branch, then rebuild and restart only when you choose to
      (`deploy/staging/setup.sh`). Re-run `deploy/staging/smoke.sh`.
- [ ] One publish on staging. Check that `/contact/#privacy` shows "How we use your message" and that the footer
      shows "How we use contact messages". This proves the worker image now ships the notice.

## 1. MFA (R-1 / F-01)
Code status: verified (tests). Enabling it is your decision.
- [ ] In the production `deploy/.env`: `MFA_ENABLED=True`. Leave `MCP_OAUTH_REQUIRE_MFA` unset (default True).
- [ ] Restart `cms` and `mcp`. Every session that signed in with only a password ends at once (by design, commit
      05e20b8). Each user signs in again and enrols an authenticator app. **Save the 10 recovery codes** in the
      password manager.
- [ ] In CMS → Claude access, use **Disconnect** for every existing Claude connection. Tokens issued while MFA was
      off are not ended by the switch; reconnect after enrolling.
- [ ] Verify: sign out, sign in with the password only. Expected: a code is asked for, and
      `GET /api/v1/auth/me/` returns 401 until it is entered.
- [ ] Staging: same steps, or keep MFA off there knowingly (it is internet-facing too, so on is recommended).

## 2. Credential rotation (R-2 / F-02): owner and CIC
Do not paste any of these into chat, email or tickets.
| Credential | Rotate how | Prove the old one is dead |
|---|---|---|
| Claude OAuth client secret (was pasted in chat) | CMS → Claude access → **Create a new client secret** (Admins). Then **Disconnect** every existing Claude connection on the same page: connections made earlier keep their current tokens until they expire. Put the new secret in claude.ai's connector settings and reconnect. | Reconnect with the old secret: the token step must fail (`invalid_client`). The new one connects. |
| Staging admin password (short) | CMS → your account → change password; 16+ characters from the password manager. Other sessions end. | Sign in with the old password: "Wrong username or password." |
| Production admin passwords | Same, for every admin, before go-live. | Same. |
| CIC SFTP password (sent by email to 7 people) | **CIC:** set a new password (or, better, key-only login for the publish agent's key). Deliver it out-of-band to one person. Restrict SFTP for that account to the campus publish PC's IP. | From another machine: `sftp <user>@<cic-host>` with the old password is refused. From the publish PC: `python -m publish_agent check` passes. |
| `AGENT_HMAC_SECRET`, `SECRET_KEY`, DB password | Fresh values in production `deploy/.env` (never reuse staging's). | `python -m publish_agent check` passes with the new agent secret. |
- [ ] Record the date of each rotation (not the value) in the handover log.

## 3. Backups and restore (R-3 / F-03)
Tooling is in `deploy/backup/`, tested 13/13 against a disposable database. Nothing has been set up on any server.
- [ ] Lab server: follow `deploy/backup/README.md` § "Set up once" (passphrase file mode 600, also kept in the
      password manager; `backup.conf`; mount the off-host folder).
- [ ] `deploy/backup/crtdh-backup.sh --dry-run`, then a real run. Expect `done`, not `FAILED`.
- [ ] `deploy/backup/crtdh-restore-check.sh latest`. Expect `PASS … users=… published_versions=… media_files=…`
      with numbers that match the CMS.
- [ ] Install the cron line from the README. Next morning, check `backup.log` and the off-host folder.
- [ ] Rehearse the full restore (README § "Full restore") once **on staging**; it is documented but not yet tried
      on a real stack.
- [ ] Campus PC: `python -m publish_agent backup` before the agent's first deploy (GO-LIVE.md §5). Copy the tarball
      off the PC.

## 4. CIC infrastructure (R-4 / F-04): CIC, with you present
Not audited. Each line needs evidence (a command's output or a screenshot), not a "should be fine".
- [ ] **TLS**: `crtdh.iitkgp.ac.in` serves a valid certificate (not expired, right name), TLS 1.2+ only, and
      http→https redirects.
- [ ] **`.htaccess` honoured**: the account has `AllowOverride FileInfo`. Check after the first publish:
      `curl -sI https://<site>/ | grep -i -E 'content-security|strict-transport|x-frame|x-content|referrer'`.
      All five present, CSP matching `build/client/.htaccess` (including `style-src-elem 'self'`). If missing, ask
      CIC to set them in the vhost; `frontend/scripts/apache-check.sh` lists them.
- [ ] **Directory listing off**: `curl -s https://<site>/_media/` shows no file index.
- [ ] **Leftover files**: list the web root before the first agent deploy. Nothing like `.git/`, `.env`, `*.bak`,
      `*.sql`, `phpinfo.php`, old CMS installs or `backup*.zip`. The agent keeps the old site as `legacy-*` outside
      `public_html`; confirm with CIC that this location is not web-served.
- [ ] **Error pages**: `/does-not-exist/` gives the site's 404 page with status 404.
- [ ] **SFTP**: per §2 (new credential, IP-restricted, chrooted to the account).
- [ ] Run `python3 tests/tools/check_headers.py --site https://<site>` from any machine; expect 0 FAIL.

## 5. Lab server (CMS / MCP / worker host): R-4
- [ ] `sudo ss -ltnp`: nothing listens on public interfaces except SSH (and, if no tunnel is used, 443 on the
      gateway). Postgres, Django, MCP and nginx are on the Docker internal network only.
- [ ] Host firewall (ufw/nftables) default-deny inbound; SSH key-only, no root login.
- [ ] `docker compose ps`: every service healthy; `docker compose config` shows `CRTDH_ENV=production`,
      `DEBUG=False`, `MFA_ENABLED=True`, and no `CRTDH_ALLOW_TEST_SEED`.
- [ ] Origin protection: if Cloudflare fronts the CMS, the origin accepts traffic only from the tunnel
      (`cloudflared`); the MCP hostname has the Anthropic-IP WAF rule (`deploy/staging/TUNNEL.md`).
- [ ] `docker compose exec gateway nginx -t` after deploying the new `gateway.conf.template` (the dot-path rule in
      commit 7893674 was validated by a test, not by `nginx -t`).
- [ ] Then: `curl -s -o /dev/null -w '%{http_code}' https://<cms>/.env` → `404`; `https://<cms>/` → `200`.
- [ ] OS and Docker updated; `docker image prune` schedule; disk space alert.
- [ ] Optional, recommended: `scripts/pin-image-digests.sh --write` on a machine with Docker, rebuild, test, then
      commit (R-11).

## 6. Security headers (all hosts)
- [ ] CMS: `python3 tests/tools/check_headers.py --cms https://<cms>`: 0 FAIL.
- [ ] Public site: §4 headers check.
- [ ] Cloudflare zone (staging and production, if used): turn **off** Email Address Obfuscation (R-10/R-12) and
      Web Analytics (the site's CSP blocks its beacon anyway). Verify: `mailto:` links are intact in the HTML source;
      no `cloudflareinsights` script on the page.

## 7. Content and privacy (R-5, R-8, R-16)
- [ ] **Grievance contact**: give a role mailbox and name or role. It goes into `docs/privacy-notice.md`
      ("Your choices" paragraph); until then that sentence is left out of the published notice. Then publish.
- [ ] Confirm the notice wording with the centre head or the institute's data-protection contact
      (`docs/privacy-notice.md` open questions).
- [ ] Turnstile: production `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET` are real keys (not Cloudflare's test keys).
      Send one real message and check that it arrives (F-16).
- [ ] CMS → Media → Media coverage: change `http://www.uniindia.com/…` to https **after** checking that the https
      link opens; change `http://pib.nic.in/…` to `https://`.
- [ ] Photos: the 8192 px image in the "Jio" gallery should be re-exported at about 2400 px (page weight).

## 8. Monitoring (R-13): owner
- [ ] A free external uptime monitor (e.g. UptimeRobot, Better Stack) on the public site (`/`, keyword
      "CRTDH"), the CMS sign-in page, and the contact host. Alert to a role mailbox, plus a phone push.
- [ ] Publish agent: an alert if "last seen" in the CMS is older than 15 minutes (or a weekly manual check).
- [ ] Disk usage on the lab server (backups grow): alert at 80%.
- [ ] Test each alert once (stop the site container on staging; confirm the alert arrives).

## 9. Final sign-off
| Item | Evidence | By | Date |
|---|---|---|---|
| Full test suites green on the release commit (TEST-RESULTS.md) | | | |
| MFA on in production, all admins enrolled | | | |
| All four credentials rotated, old ones proven dead | | | |
| Backup running nightly, restore-check PASS, off-host copy present | | | |
| CIC checklist §4 complete, headers 0 FAIL | | | |
| Lab server checklist §5 complete | | | |
| Privacy notice with grievance contact live and approved | | | |
| Uptime alerts tested | | | |
| Owner go/no-go | | Annjan | |
