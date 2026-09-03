# CRTDH Admin SPA

A bespoke, on-brand React admin panel for the CRTDH CMS rebuild. Non-technical staff use this app to create, edit,
reorder, and delete every piece of content on the public site — no code changes required. Built against
`API_CONTRACT.md` at the repo root; see that file for the authoritative field list of every resource.

## Stack

- [Vite](https://vitejs.dev/) + React 19, plain JavaScript (JSX)
- [react-router-dom](https://reactrouter.com/) for routing and route guards
- [axios](https://axios-http.com/) for the API client, with a response interceptor that silently refreshes the JWT
  access token on a 401
- [@dnd-kit/core](https://dndkit.com/) + `@dnd-kit/sortable` for drag-and-drop reordering
- [@tiptap/react](https://tiptap.dev/) + `@tiptap/starter-kit` for the `Innovation.body` rich text editor
- Hand-rolled CSS design system (sidebar + content shell, cards, tables, forms, modal) — no external UI kit, kept
  light and consistent

No backend code lives in this directory — it only talks to the Django REST API described in `API_CONTRACT.md`.

## Running the dev server

```bash
npm install
npm run dev
```

This starts Vite on `http://localhost:5174` (the admin origin the backend's dev CORS settings already allow, per
`API_CONTRACT.md`). The app expects the Django API to be running and reachable at the URL configured below.

## Configuring the API base URL

The API base URL is read from the `VITE_API_BASE_URL` environment variable at build/dev time. Copy the example env
file and adjust it:

```bash
cp .env.example .env.local
```

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

If unset, it falls back to `http://localhost:8000/api/v1` (the contract's dev default). In production, set this to
your deployed API's `/api/v1` URL before running `npm run build` (Vite inlines env vars at build time — there is no
runtime override once built, so the Docker image must be built with the right value, or the compose/deploy setup
should build per-environment).

## Building for production

```bash
npm run build
```

Outputs static assets to `dist/`. Serve them with any static file server (see `Dockerfile` for the nginx-based
production image) — this is a client-side-only SPA with no server component of its own; make sure the web server
falls back unknown paths to `index.html` so client-side routes like `/resources/team-members/3` work on a hard
refresh (the provided `Dockerfile`/nginx config does this).

```bash
npm run preview   # serve the dist/ build locally to sanity-check it
```

## Authentication

- Login posts `{username, password}` to `POST /api/v1/auth/token/`, storing the returned `access`/`refresh` tokens
  in `localStorage` (acceptable for this internal staff tool).
- Every API call carries `Authorization: Bearer <access>` (added by the axios request interceptor in
  `src/api/client.js`).
- On a `401`, the response interceptor calls `POST /api/v1/auth/token/refresh/` once, retries the original request
  with the new access token, and if the refresh itself fails, clears storage and redirects to `/login`.
- `GET /api/v1/auth/me/` is called once on app load (`AuthContext`) to confirm the stored token is still valid and
  to gate every route in `<ProtectedRoute>` behind a real session, not just "a token exists in storage".

## The generic CRUD schema pattern

Almost every resource in the contract shares the same shape: a paginated list with an `order` field, a
create/edit form, image or file uploads, and a `/reorder/` action. Rather than hand-writing ~20 nearly-identical
list+form screens, this app defines **one generic `ResourceCrudPage` pattern** — `ResourceListPage` (list + reorder
+ delete) and `ResourceFormPage` (create/edit form, plus inline nested-child managers where relevant) — and drives
both purely from a **schema config**: `src/resources/schemas.js`.

Each entry in `RESOURCE_SCHEMAS` describes one resource:

```js
{
  key: 'team-members',              // used in the route: /resources/team-members
  label: 'Team Members',            // shown in nav, list, and form headings
  group: 'Team',                    // sidebar/dashboard grouping
  endpoint: '/team-members/',       // API path
  orderable: true,                  // renders as a drag-and-drop list, wired to /reorder/
  fields: [
    { name: 'category', label: 'Category', type: 'select',
      optionsEndpoint: '/team-categories/', optionLabel: 'name', required: true },
    { name: 'name', label: 'Name', type: 'text', required: true },
    { name: 'photo', label: 'Photo', type: 'image' },
  ],
  listColumns: ['photo', 'name', 'category_name'],
}
```

Field `type` drives which control renders (`text` / `textarea` / `richtext` / `number` / `select` / `image` /
`file`) — see `src/components/FormField.jsx` for the single switch statement that maps types to inputs, and
`src/components/ImageUploadField.jsx` / `RichTextEditor.jsx` for the upload and Tiptap widgets specifically. A
`select` field either takes a static `options` array (e.g. `Document.category`'s enum) or `optionsEndpoint` +
`optionLabel` to populate itself from another resource (FK pickers).

For parents with nested children per the contract (`Innovation`→`InnovationImage`, `Product`→`ProductImage`/
`ProductPartner`, `MediaEvent`→`MediaEventImage`, `ImageGridBlock`→`ImageGridItem`), the schema adds a `children`
array; `ResourceFormPage` renders one `<ChildResourceManager>` per entry on the edit screen, which adds/edits/
deletes/reorders the child rows against their own top-level endpoint (e.g. `/innovation-images/`) with the parent
FK set automatically — staff never have to leave the parent's page or visit a separate screen for the images.

**To add a brand-new resource once the backend adds one**, add one object to `RESOURCE_SCHEMAS` (or one entry to an
existing resource's `children` array for a new nested type) with its endpoint, fields, `orderable`, and
`listColumns`. That's it — the sidebar, dashboard cards, list view, create/edit form, image upload, and reorder all
read this config automatically; no new page component is needed. The only resource that intentionally does *not*
go through this pattern is `site-settings` (`src/pages/SiteSettingsPage.jsx`), since it's a GET/PATCH singleton
with no list, id, or reorder semantics, and `contact-messages` (`src/pages/ContactMessagesPage.jsx`), which is
read-only-plus-delete with no create/edit form at all.

## Project layout

```
src/
  api/
    client.js       axios instance, token storage, 401-refresh interceptor
    auth.js         login / fetchMe / logout
    resources.js    generic list/get/create/update/delete/reorder helpers
  context/
    AuthContext.jsx session state, gates routing
  components/
    ProtectedRoute.jsx      route guard
    Layout.jsx               sidebar + topbar shell
    FormField.jsx             field-type → input renderer
    ImageUploadField.jsx      drag/click image & file upload with preview
    RichTextEditor.jsx        Tiptap wrapper for Innovation.body
    SortableList.jsx          generic dnd-kit reorderable list
    ChildResourceManager.jsx  inline nested-child CRUD (images, partners, ...)
    ConfirmDialog.jsx         delete confirmation modal
    Spinner.jsx
  pages/
    LoginPage.jsx
    DashboardPage.jsx        one card per resource, generated from the schema
    SiteSettingsPage.jsx     singleton form (the one non-generic resource)
    ContactMessagesPage.jsx  read-only list + delete
    ResourceListPage.jsx     generic list/reorder/delete for any resource
    ResourceFormPage.jsx     generic create/edit form (+ nested children)
    NotFoundPage.jsx
  resources/
    schemas.js       the schema config described above — the source of truth
  index.css           hand-rolled design system
  App.jsx             route tree
  main.jsx             entry point
```

## Deployment

See `Dockerfile` — a multi-stage build (Node to `npm run build`, then nginx serving the static `dist/` output with
SPA fallback routing). Wire it into `deploy/docker-compose.yml` alongside the backend and public frontend.
