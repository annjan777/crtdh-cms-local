# CRTDH CMS — API Contract (authoritative, shared by backend/frontend/admin)

Base URL: `/api/v1/`. All list endpoints are DRF `ModelViewSet`s registered on a `DefaultRouter`, paginated with
`PageNumberPagination` (`page_size=100`), returning `{count, next, previous, results}`. Detail routes are
`/api/v1/<resource>/<id>/`. All `image`/`file` fields serialize to **absolute URLs** (built with `request` in
serializer context). Every listable model has an integer `order` field (default ascending) and a
`POST /api/v1/<resource>/reorder/` action taking `{"order": [id, id, id, ...]}` (full ordered id list for that
resource) and re-numbering `order` accordingly — staff-only.

**Auth**: JWT via `djangorestframework-simplejwt`.
- `POST /api/v1/auth/token/` `{username, password}` → `{access, refresh}`
- `POST /api/v1/auth/token/refresh/` `{refresh}` → `{access}`
- `GET /api/v1/auth/me/` (authenticated) → `{id, username, email, is_staff}`
Admin SPA sends `Authorization: Bearer <access>`. All non-GET requests on every resource below require
`IsAdminUser` (staff). All GET requests are public/unauthenticated. CORS allowed origins come from env var
`CORS_ALLOWED_ORIGINS` (comma-separated); dev defaults include `http://localhost:5173` (public frontend) and
`http://localhost:5174` (admin SPA).

## Resources

### Site settings (singleton)
`GET/PATCH /api/v1/site-settings/` — no list, always a single object (get_or_create pk=1).
Fields: `address, phone_primary, phone_secondary, email_primary, email_secondary, map_embed_url, facebook_url, linkedin_url, instagram_url, twitter_url`

### Nav items
`/api/v1/nav-items/` — `id, label, url, order`

### Carousels
`/api/v1/hero-slides/` — `id, image, order`
`/api/v1/project-slides/` — `id, image, title, order`

### Team
`/api/v1/team-categories/` — `id, name, order`
`/api/v1/team-members/` — `id, category, category_name (read-only), name, photo, order` (`category` = FK id, filterable via `?category=<id>`)

### Facilities
`/api/v1/equipment/` — `id, name, image, order`

### Services
`/api/v1/services/` — `id, title, image, order`

### Innovations
`/api/v1/innovations/` — `id, title, body (sanitized HTML), video_url, order, images (nested read-only list of InnovationImage)`
`/api/v1/innovation-images/` — `id, innovation, image, caption, order` (write endpoint for nested images; `innovation` = FK id, filterable via `?innovation=<id>`)

### Products
`/api/v1/products/` — `id, name, order, images (nested read-only), partners (nested read-only)`
`/api/v1/product-images/` — `id, product, image, order`
`/api/v1/product-partners/` — `id, product, name, logo (nullable)`

### Enterprises
`/api/v1/enterprises/` — `id, name, subtitle, logo (nullable), order`

### Media / gallery
`/api/v1/media-events/` — `id, title, slug (unique), order, images (nested read-only)`
`/api/v1/media-event-images/` — `id, event, image, caption, order`
`/api/v1/media-coverage-links/` — `id, title, url, order`
`/api/v1/gallery-images/` — `id, image, caption, order`

### Generic image grids (facilities-manufacturing, services images, enterprises demo grid, social-impact/covid-19 grids)
`/api/v1/image-grid-blocks/` — `id, page (slug-like string, e.g. "facilities"), section_title, anchor_slug, items (nested read-only)`
`/api/v1/image-grid-items/` — `id, block, image, caption, order`

### Video blocks
`/api/v1/video-blocks/` — `id, title, page, youtube_url (nullable), video_file (nullable), order`

### Documents (PDFs)
`/api/v1/documents/` — `id, title, file, category (enum: newsletter|membership|other), order`

### About-page structured content
`/api/v1/focus-areas/` — `id, title, color, order`
`/api/v1/objective-rows/` — `id, task, outcome, order`
`/api/v1/timeline-entries/` — `id, year, title, image, order`

### Homepage news marquee
`/api/v1/news-items/` — `id, text, link_url, order`

### Contact
`POST /api/v1/contact/` (public) — in: `{name, email, phone, message}` → creates a message, returns 201.
`/api/v1/contact-messages/` (staff only, GET list + DELETE) — `id, name, email, phone, message, created_at`

## Pages → resources used (for frontend routing reference)

- **Home** (`/`): hero-slides, news-items, site-settings (map), a couple of image-grid-blocks (`page=home`)
- **About** (`/about`): focus-areas, objective-rows, timeline-entries, documents (category=other, the PI-desk write-up)
- **Team** (`/team`): team-categories + team-members
- **Innovations** (`/innovations`): innovations (incl. nested images, project-slides for the one with a carousel)
- **Facilities** (`/facilities`): equipment, image-grid-blocks (`page=facilities`)
- **Services** (`/services`): services
- **Enterprises** (`/enterprises`): enterprises, image-grid-blocks (`page=enterprises`), video-blocks (`page=enterprises`)
- **Product** (`/product`): products (incl. nested images/partners)
- **Social Impact** (`/social-impact`): image-grid-blocks (`page=social-impact`), video-blocks (`page=social-impact`)
- **Covid-19** (`/covid-19`): image-grid-blocks (`page=covid-19`), video-blocks (`page=covid-19`)
- **Media** (`/media`): media-events (+ nested images), media-coverage-links, gallery-images
- **Contact** (`/contact`): site-settings, POST contact

Every page also uses **nav-items** and **site-settings** (footer) globally.
