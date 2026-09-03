# CRTDH Public Frontend

The public-facing website for CRTDH (Common Research and Technology Development Hub on
Affordable Healthcare), IIT Kharagpur. A Vite + React (JavaScript) single-page app, styled with
plain CSS (no framework), consuming the read-only public endpoints of the Django REST Framework
backend described in `../API_CONTRACT.md`.

## Stack

- **Vite** + **React 19** (JavaScript, function components + hooks)
- **React Router v7** — one route per page, matching the API contract's page list
- **Embla Carousel** (`embla-carousel-react`) — hero slides / project slides / product image
  carousels
- Hand-written global CSS design system (`src/styles/tokens.css` + `src/styles/global.css`) plus
  small per-page/component stylesheets — no Tailwind/Bootstrap
- No state management library — data fetching is local to each page via a small `useApi` hook

## Getting started

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` by default (matches the CORS origin the backend
expects for the public frontend, per `API_CONTRACT.md`).

## Configuring the API base URL

The app reads the backend's base URL from the Vite env var `VITE_API_BASE_URL`. Copy the example
env file and adjust as needed:

```bash
cp .env.example .env.local
```

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

If the variable is unset, the app falls back to `http://localhost:8000/api/v1` for local
development. For a production build, set `VITE_API_BASE_URL` to the deployed backend's public API
URL (e.g. `https://crtdh.example.com/api/v1`) before running `npm run build` — Vite inlines env
vars at build time.

## Building for production

```bash
npm run build
```

Outputs a static `dist/` folder. Preview it locally with:

```bash
npm run preview
```

The included `Dockerfile` builds `dist/` in a Node stage and serves it with nginx (see
`nginx.conf`), matching the deploy plan's static-frontend container.

## Resilience to a missing/unreachable backend

Every page fetches its own data through `src/api/client.js`, which:

- Never throws into a component from a failed `fetch` (network error, non-2xx, bad JSON) — list
  endpoints resolve to `[]`, single-object endpoints resolve to `null`.
- Is paired with `src/hooks/useApi.js`, which tracks `loading`/`error`/`data` and is rendered via
  `src/components/StateBlock.jsx` (`Spinner` / `EmptyState` / `ErrorState` / `DataState`), so every
  page shows a loading skeleton, then either real content or a friendly empty/error state — never
  a crash or blank screen — even when the backend is completely unreachable.
- The contact form's `POST /contact/` is the one exception that intentionally surfaces errors (via
  `postJSON`, which throws), since the form needs to tell the user their message did not send.

## Project structure

```
src/
  api/client.js            fetch wrapper: API_BASE_URL, fetchList, fetchOne, postJSON
  hooks/useApi.js          loading/error/data hook wrapping the api client
  context/SiteDataContext.jsx  nav-items + site-settings, fetched once in Layout
  components/              Layout (header/nav/footer), Carousel, ImageGrid,
                            ImageGridBlockSection, VideoBlock, PageHero, StateBlock
  pages/                   one file per route (Home, About, Team, Innovations,
                            Facilities, Services, Enterprises, Product, SocialImpact,
                            Covid19, Media, Contact, NotFound)
  styles/tokens.css        design tokens (color, type, spacing, radius, shadow)
  styles/global.css        reset + base typography + shared utility classes
```

## Notes / deviations

- `Innovation.body` is rendered via `dangerouslySetInnerHTML` per the contract, since the backend
  sanitizes it with `bleach` before storage.
- `/project-slides/` has no FK back to a specific innovation in the contract, so the Innovations
  page renders it as a single page-level "Project spotlight" carousel rather than attaching it to
  one card.
- `image-grid-blocks` and `video-blocks` are requested with a `?page=<slug>` query param (per the
  generic reuse described in the contract) and additionally filtered client-side by `block.page`,
  so the page still renders correctly even if the backend doesn't yet support that filter.
- Media page deep links (e.g. `/media#pathologyandeyeclinic`) are preserved: each `MediaEvent` is
  rendered as `<section id={event.slug}>`, and a `useEffect` scrolls to `location.hash` once data
  has loaded.
