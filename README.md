# CRTDH website and CMS

The website of the Common Research & Technology Development Hub (CRTDH) on Affordable Healthcare, IIT Kharagpur,
and the private CMS that lab staff use to edit it.

The public site at https://crtdh.iitkgp.ac.in/ is **static files only**: no server code, no database, nothing
writable. Staff edit a private copy in the CMS and publish. A publish builds the whole site and an agent on the
one allowed campus PC uploads it.

## The four parts

| Part | Folder | What it is |
|---|---|---|
| **Public site** | `frontend/` | React Router 7, prerendered to static HTML from a published snapshot. Design rules: `frontend/DESIGN.md` |
| **CMS** | `backend/` + `admin/` | Django 5 / DRF API with Postgres, session + TOTP sign-in, drafts, snapshots and audit log (`backend/apps/publishing`). React admin that edits the real page section by section |
| **Claude connector (MCP)** | `backend/mcp_server/`, `backend/apps/oauth/` | Remote MCP server with OAuth. Lets a signed-in editor ask Claude for changes, which are saved as unpublished drafts only |
| **Publish agent** | `publish_agent/` | Small Python program on campus PC 10.111.26.20. Fetches signed builds from the CMS, uploads them to `academicweb.iitkgp.ac.in` over SFTP, switches atomically, can roll back |

Production layout (lab server, Cloudflare Tunnel, no inbound ports): `deploy/`. The diagram is in
[docs/HANDOVER.md](docs/HANDOVER.md#1-architecture).

## Docs

| Read this | If you are |
|---|---|
| [docs/GO-LIVE.md](docs/GO-LIVE.md) | deploying from zero to live (ordered runbook, with checks and rollbacks) |
| [docs/HANDOVER.md](docs/HANDOVER.md) | the developer who runs it after 31 Jan 2027: architecture, secrets, backups, incidents, sign-off |
| [docs/STAFF-GUIDE.md](docs/STAFF-GUIDE.md) | lab staff editing the website |
| [docs/connect-claude.md](docs/connect-claude.md) | staff connecting Claude to the CMS |
| [deploy/README.md](deploy/README.md) | operating the Docker stack on the lab server |
| [publish_agent/README.md](publish_agent/README.md) | installing or fixing the campus publish agent |
| [docs/mcp.md](docs/mcp.md) | maintaining the Claude/MCP server |
| [docs/testing.md](docs/testing.md), [docs/uat/](docs/uat/README.md) | testing, and user acceptance runs |
| [API_CONTRACT.md](API_CONTRACT.md), [docs/contracts/](docs/contracts/) | the API |
| [docs/cms-mapping.md](docs/cms-mapping.md) | moving from the old admin screens |
| [docs/content-gaps.md](docs/content-gaps.md), [docs/privacy-notice.md](docs/privacy-notice.md) | content and privacy text that still needs a human |

## Quick start for developers

There is no `make dev` yet. These are the real commands. They need Python 3.12, Node 20, and optionally
Postgres 16.

**Backend (SQLite, seeded content):**

```bash
cd backend
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                       # DEBUG=True, SQLite
python manage.py migrate
python manage.py bootstrap_local           # loads the bundled content and seed_media (dev only)
python manage.py create_dev_users          # one user per role; prints random passwords once
python manage.py runserver 8300            # the admin dev server proxies /api to :8300
```

**Admin (CMS editor):**

```bash
cd frontend && npm ci && cd ../admin && npm ci   # the canvas imports frontend/src/site
VITE_USE_MOCK=1 npm run dev     # http://localhost:3200 with an in-browser fake API (test users in admin/README.md)
npm run dev                     # same, against the backend on :8300
```

**Public site:** `cd frontend && npm ci && SNAPSHOT_PATH=/path/to/snapshot.json npm run build`. A snapshot comes
from a CMS publish: the worker writes `builds/<publish id>/snapshot.json` under `PUBLISH_ROOT` (default
`backend/var/publish`). Start a publish in the admin, then run
`cd backend && python manage.py run_publish_worker --once`.

**Whole stack with production settings** (Postgres, gunicorn, MCP, worker, fake CIC SFTP host, publish agent,
HTTPS):

```bash
scripts/preprod.sh up      # then: smoke | e2e | status | down
```

**Tests:**

```bash
cd backend && pytest                                   # unit; add --integration for SIT
python -m pytest publish_agent/tests -p no:asyncio
cd frontend && npm test;  cd admin && npm test
```

Details, CI gates and security scans: [docs/testing.md](docs/testing.md).

`docker-compose.local.yml` runs the database, backend and admin only. The public site is static: build and
preview it as in `frontend/README.md`, or run the whole publish flow with `scripts/preprod.sh`.

## Rules

- Never commit secrets. `deploy/.env`, `deploy/cloudflared/config.yml` and `credentials.json` are gitignored.
- No default or seed users anywhere. Production users are created with `createsuperuser` and the **Users** screen.
- Every content write goes through `apps.publishing` (CI checks the import contracts and write paths).
