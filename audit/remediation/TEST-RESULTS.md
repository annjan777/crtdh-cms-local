# Test results: `v3/remediation` (final code, 2026-11-20)

All runs were in the cloud sandbox. Nothing ran against staging or production. Logs are in `test-results/remediation/` (gitleaks: 0 findings; no TOTP seed values).

| Suite | Command | Result | Baseline at 1f29d21 |
|---|---|---|---|
| Backend incl. integration | `cd backend && pytest --integration` | **1267 passed**, 0 failed | 1260 passed |
| Publish agent | `pytest publish_agent/tests` | **105 passed** | 104 |
| Admin unit | `cd admin && npx vitest run` | **58 passed** | 58 |
| Admin browser (mock CMS) | `cd admin && npx playwright test` | **61 passed** | 49 passed, **8 failed** (F-17) |
| Frontend unit | `cd frontend && npx vitest run` | **99 passed** | 99 |
| Public-site browser | `CONTACT_API_URL=https://contact.crtdh.test/api/v1/contact/ npm run build && npx playwright test` | **156 passed** (+28 new: embeds, CSP) | 128 |
| Full-stack E2E (rehearsal: Postgres 16, gunicorn, MCP, worker, agent, fake CIC SFTP), wiped state | `scripts/preprod.sh down --wipe && up && smoke && e2e` | **208 passed**, 2 skipped, 0 failed | first run on this branch: 181 passed / 21 failed / 6 errors (causes in CODE-CHANGES R-6) |
| Preprod smoke (edit → publish → live on fake CIC) | `scripts/preprod.sh smoke` | PASS | — |
| Backup scripts | `tests/tools/test_backup_scripts.sh` | **13/13** (includes a real restore) | — |
| Secrets scan of the new commits and evidence | `gitleaks git --log-opts=1f29d21..HEAD`; `gitleaks dir test-results/remediation` | 0 findings | — |

New tests were checked against the old code. R-7 (2 of 4), R-1 (3 of 3) and R-6 fail there and pass now.

The 2 E2E skips are by design: one MCP check needs a real claude.ai, and one visual spec needs a baseline.

## Not tested
| What | Why |
|---|---|
| Worker/agent/sftp **Docker image builds** (notice COPY, agent USER) | No Docker in the sandbox; covered by config tests only. Build on staging. |
| `nginx -t` on the new gateway rule | No nginx here; validated by a regex test. Run in the gateway container. |
| Trivy CI job, digest pinning | No CI run (nothing pushed); Docker Hub unreachable. |
| Full restore into a live stack | Only the throwaway restore check was run. |
| Anything on staging, the lab server, CIC Apache | Out of bounds (owner/CIC actions, PRODUCTION-CHECKLIST). |
| Real Turnstile + SMTP contact send, real claude.ai connector | External services. |
