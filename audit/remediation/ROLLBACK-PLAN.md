# Rollback plan: `v3/remediation`

Every change is a separate commit on `v3/remediation` (base `1f29d21`). None of them changes the database
schema: **there are no migrations**, so code can go back without touching data. To undo one change:
`git revert <commit>`, then rebuild only the image it affects. To undo everything: deploy `1f29d21` again.

Rebuild hints (staging, homelab): `deploy/staging/dc.sh build <service> && deploy/staging/dc.sh up -d <service>`,
when you choose. Production: the same with `docker compose`. The public site changes only on the next publish.

| Commit | Change | Affects | Undo | Side effects of undoing |
|---|---|---|---|---|
| f5acd2c | Editor drops leftover drafts that match the CMS; Discard button (R-7) | admin image | revert; rebuild `admin` | The false "unsaved change" warning returns. Drafts in browsers are untouched either way. |
| 87a695c | Light footer; justification only on wide screens | public site (worker image) | revert; rebuild `worker`; publish | Dark footer returns. |
| 385f217 | Worker image ships the privacy notice; footer privacy link (R-5) | worker image | revert; rebuild `worker`; publish | The notice disappears from the site again. |
| 930dcee | Click-to-load map and videos; Get Directions link; notice text (R-8) | worker image | revert; rebuild `worker`; publish | Google/YouTube load on every page view again. CSP stays compatible either way. |
| 2356230 | Justify only long body text | worker image | revert; rebuild; publish | Cosmetic only. |
| 517c784 | Admin browser tests updated; 2 workers | tests only | revert | None at runtime. |
| 05e20b8 | MFA: password-only sessions stop counting once MFA is on (R-1) | backend image (`cms`, `mcp`) | revert; rebuild `cms` and `mcp` | With MFA off, no visible change. With MFA on, password-only sessions from before the switch would be accepted again. **Deploying** this commit while MFA is on signs out sessions that predate it (they have no method recorded): users sign in again once. |
| a64961f | Test-seed guards (tests only) | tests | revert | None. |
| 7893674 | Gateway 404 for dot-paths; agent HMAC over path + query (R-17) | gateway config, backend, publish agent | revert; redeploy gateway (`nginx -t` first) and `cms`; reinstall agent if updated | Agent and CMS stay compatible in **either order**: the agent sends no query strings, so the signed string is identical. |
| e84189a | Agent image USER nobody; Trivy CI job; digest script (R-11) | staging agent image, CI | revert; rebuild `publish-agent` | None (compose already sets the user). |
| ea9edc7 | axe-playwright-python in dev requirements | tests | revert | Accessibility E2E cannot run. |
| f50879b | CSP: `style-src-elem 'self'`, `style-src-attr 'unsafe-inline'` (R-15) | public site `.htaccess` (worker) | revert; rebuild `worker`; publish | Back to `style-src 'self' 'unsafe-inline'` only. If a page ever needs an inline `<style>`, this is the commit to look at. |
| a791575 | Backup and restore-check scripts (R-3) | new files only | revert, or simply remove the cron line | Nothing runs unless you installed the cron line. Existing backup sets stay where they are. |
| be95d37 | E2E fixes; rehearsal MFA on; golden re-baselined; Home hides photo-less slides | tests, `scripts/preprod.sh`, worker image | revert; rebuild `worker`; publish | A slide without a photo shows an empty image again. Old golden kept in `tests/e2e/golden/public_content.v2-v3design.json`. |
| 40ff3c6 → 2d7f87d | PIB link in the seed: added, then reverted | none (net zero) | nothing to undo | None. |
| 2453bdc | Golden `/media` heading | tests only | revert | Golden test fails on correct content. |

## Operational changes (when you make them; not done by this work)
| Action | Undo |
|---|---|
| `MFA_ENABLED=True` | Set it to False and restart `cms`/`mcp`. Enrolments are kept and reused if it goes back on. Everyone signs in again. |
| Credential rotation | Not reversible by design. Keep the new values in the password manager before the old ones stop working. |
| Backup cron | Remove the line (`crontab -e`). Delete sets only on purpose. |
| Cloudflare: Email Obfuscation / Web Analytics off | Toggle back on in the zone settings. |
| Digest pinning (`scripts/pin-image-digests.sh --write`) | `git checkout -- '*Dockerfile'` before committing, or revert the commit. |
