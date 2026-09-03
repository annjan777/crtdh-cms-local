# CRTDH CMS — Backend (Django + DRF)

The API backend for the CRTDH CMS rebuild. Implements every resource in
[`../API_CONTRACT.md`](../API_CONTRACT.md) — that document is the source of
truth for endpoint paths, field names and behavior; this README only covers
running and operating this service.

## Stack

Django 5 + Django REST Framework, `djangorestframework-simplejwt` for auth,
`django-cors-headers`, `django-filter` for `?field=` query filtering,
`django-environ` for `.env`-based settings, Pillow for image fields, `bleach`
for sanitizing `Innovation.body` rich text on save. PostgreSQL in
production/docker; sqlite works fine for local dev via a `DATABASE_URL`
override.

## Running locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum, for local dev without postgres running you can
# point DATABASE_URL at sqlite instead of the docker-compose default:
#   DATABASE_URL=sqlite:///db.sqlite3

python manage.py migrate
python manage.py createsuperuser   # or: python manage.py createstaffuser
python manage.py runserver
```

The API is then live at `http://127.0.0.1:8000/api/v1/`.

### Creating a staff user

The project uses Django's built-in `User` model unmodified — its `is_staff`
flag is exactly what every write endpoint checks. `python manage.py
createsuperuser` works out of the box and is the simplest path (superusers
are staff). There's also a `createstaffuser` management command
(`apps/core/management/commands/createstaffuser.py`) that's a thin,
identically-behaved alias, for a more obviously-named entry point in scripts.
For a staff-but-not-superuser account, use the Django shell:

```python
from django.contrib.auth.models import User
User.objects.create_user("alice", "alice@example.com", "change-me", is_staff=True)
```

### Media & static files

`MEDIA_ROOT=backend/media`, served at `/media/` (via `runserver` in `DEBUG`,
via a reverse proxy / volume in production). `STATIC_ROOT=backend/staticfiles`
for `collectstatic` in production.

## Seeding content from the old static site

`python manage.py seed_from_mirror` populates a fresh/dev database from the
scraped HTML mirror of the original static site
(`apps/core/management/commands/seed_from_mirror.py`). It parses the
mirror's HTML with BeautifulSoup for every well-structured, repeating
section (carousels, team, facilities equipment + manufacturing grid,
services, enterprises + demonstration grid, media galleries + coverage
links + top gallery, nav, site settings/footer, and the newsletter/
membership PDFs), and copies each referenced image/PDF into the matching
model's `ImageField`/`FileField` under `MEDIA_ROOT`. The 12 Innovations
and 5 Products pages are irregular, hand-built layouts that don't parse
reliably as a loop, so their content is hand-authored (real body text and
image references, taken from actually reading the source pages) in
`apps/core/management/commands/_seed_data/{innovations,products}.json`
and loaded verbatim.

```bash
# Defaults to /home/claude/crtdh_mirror/site — override if the mirror lives
# somewhere else on your machine:
python manage.py seed_from_mirror --mirror-path /path/to/crtdh_mirror/site
```

Meant to be run **once**, against a fresh/dev database, to bootstrap
content before handing the site off to the admin SPA — not an incremental
sync tool. It's safe to re-run (each section is cleared and recreated from
the mirror, so re-running never accumulates duplicates), but a re-run also
wipes any edits made since in the admin SPA to the models it owns.
`SiteSettings` is the one exception — it's a true singleton and gets
updated in place rather than deleted. A handful of images the old site
references were never actually captured in the mirror (an external
`via.placeholder.com` URL, one malformed `src`, a couple of missing
filenames) — those are skipped rather than crashing the run, and every
skip is listed in the summary the command prints at the end alongside the
row count created per model.

## JWT auth flow (for the admin SPA)

1. `POST /api/v1/auth/token/` with `{"username", "password"}` → `{"access", "refresh"}`.
2. Send `Authorization: Bearer <access>` on every subsequent request. Access
   tokens last 1 hour.
3. When the access token expires, `POST /api/v1/auth/token/refresh/` with
   `{"refresh"}` → a new `{"access"}`.
4. `GET /api/v1/auth/me/` (any authenticated user) → `{id, username, email,
   is_staff}` — use this to confirm the logged-in account is staff and to
   populate the admin SPA's "logged in as" UI.

All `GET` requests across every resource are public/unauthenticated. Every
non-`GET` request (create/update/delete, and the `reorder` action) requires
`request.user.is_staff` — enforced by the shared `IsAdminOrReadOnly`
permission class (`apps/common/permissions.py`), applied to every viewset.
The one deliberate exception is `POST /api/v1/contact/`, which is `AllowAny`
(it's the public contact form) — reading/deleting submitted messages is done
through the separate, staff-only `/api/v1/contact-messages/` endpoint.

## Ordering & reorder

Every model with an `order` field defaults `Meta.ordering = ["order"]`, so
list endpoints return rows in that order by default. Each such resource's
viewset also exposes `POST /api/v1/<resource>/reorder/`, taking
`{"order": [id, id, id, ...]}` — the full ordered list of ids for that
resource (or for the currently-filtered queryset, if you pass the same
filter query params) — and re-numbers `order` to match. Staff-only, same as
any other write. Two resources have no `order` field per the contract
(`ImageGridBlock` — its items are ordered instead — and `ProductPartner`) and
so have no `reorder` action.

## Filtering

`?category=<id>` on `/api/v1/team-members/`, `?innovation=<id>` on
`/api/v1/innovation-images/`, `?product=<id>` on `/api/v1/product-images/`
and `/api/v1/product-partners/`, `?event=<id>` on
`/api/v1/media-event-images/`, `?block=<id>` on `/api/v1/image-grid-items/`,
`?page=<slug>` on `/api/v1/image-grid-blocks/` and `/api/v1/video-blocks/`,
`?category=<newsletter|membership|other>` on `/api/v1/documents/` — all via
`django-filter`.

## API endpoints

See [`../API_CONTRACT.md`](../API_CONTRACT.md) for the complete, authoritative
list of resources, fields, and per-page usage — every path there is wired up
exactly as written. In short: one `ModelViewSet` per resource on a DRF
`DefaultRouter` under `/api/v1/`, plus the singleton `/api/v1/site-settings/`
(GET/PATCH APIView), the public `/api/v1/contact/` (POST-only APIView), and
the three JWT auth endpoints above.

## Deployment

See `Dockerfile` (installs `requirements.txt`, runs
`gunicorn config.wsgi:application --bind 0.0.0.0:8000`) and
`../deploy/docker-compose.yml` for the full stack. Migrations are expected to
run as a separate step/command override (e.g.
`python manage.py migrate && gunicorn ...`) rather than baked into the image's
default `CMD`. `DATABASE_URL` defaults to
`postgres://crtdh:crtdh@db:5432/crtdh`, matching the `db` service name in
docker-compose; override it via `.env` for any other environment.

## Verification performed during development

- `python manage.py check` — clean.
- `python manage.py makemigrations` + `migrate` — clean for every app
  (against a local sqlite override; the checked-in default stays postgres).
- All 25 list endpoints (`nav-items`, `team-members`, `site-settings`, etc.)
  return `200` with the paginated `{count, next, previous, results}` shape
  (or the singleton object, for `site-settings`).
- JWT flow: obtained a token via `/api/v1/auth/token/`, confirmed
  `/api/v1/auth/me/` returns the expected profile, confirmed a write
  succeeds with the token and fails `401` without it.
- `reorder` action verified on `/api/v1/nav-items/reorder/`, including its
  `400` validation when the id list doesn't exactly match the resource.
- Image upload verified to serialize to an absolute URL
  (`http://.../media/hero_slides/....jpg`).
- Nested read-only serializers verified (`Innovation.images`,
  `TeamMember.category_name`), and `?category=`/`?innovation=` filtering.
- `Innovation.body` bleach sanitization verified: a `<script>` tag and an
  `onclick` attribute submitted in `body` were stripped on save.
- Contact flow verified end-to-end: public `POST /api/v1/contact/` (201,
  no auth), `GET`/`DELETE` on `/api/v1/contact-messages/` correctly gated to
  staff (`401` unauthenticated, works with a staff token).
