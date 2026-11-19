# Old admin managers → new page editor

The v2 admin had one screen per database table. The v3 editor (`admin/`) is organised by public page and
section, from the registry in `backend/apps/publishing/registry.py`. Every resource the old screens edited is in
that registry, so every old screen has a new home. Open a page in the editor and pick the numbered section.

| Old screen (route) | Resource(s) | New place: page → section |
|---|---|---|
| Dashboard (`/`) | — | Removed. The editor opens on Home; the draft bar shows unpublished changes; Review & publish lists them |
| Login (`/login`) | `auth/token/` (JWT) | Sign-in screens: password → authenticator code; first-time enrolment; temporary-password change |
| Home page settings (`/home-page`), Home sections editor | `home-page` | Home → Why CRTDH exists, Membership, Enterprises, MSME map, Rural healthcare, Facility cards, Videos, Visit us |
| Hero carousel manager (`/hero-manager`) | `hero-slides` | Home → Hero (photo with 16:9 / 4:5 crops and focus point, alt text required) |
| News items (`/resources/news-items`) | `news-items` | Home → News ticker |
| About page (`/about-page`) | `about-page` | About → Intro, Ecosystem, Note from the PI, Partners |
| Focus areas, Objective rows, Timeline | `focus-areas`, `objective-rows`, `timeline-entries` | About → Focus areas, Support, Timeline |
| Team manager (`/team-manager`), Team categories | `team-members`, `team-categories` | Team → Members, Groups |
| Project slides | `project-slides` | Innovations → Spotlight |
| Innovations (+ images) | `innovations`, `innovation-images` | Innovations → List (images as a child list of each innovation) |
| Equipment | `equipment` | Facilities → Equipment |
| Image grid blocks (+ items) | `image-grid-blocks`, `image-grid-items` | Photo sections on Facilities, Enterprises, Social Impact, Covid-19 (filtered by page) |
| Services | `services` | Services → List |
| Products (+ images, partners) | `products`, `product-images`, `product-partners` | Product → List |
| Enterprises | `enterprises` | Enterprises → List |
| Video blocks | `video-blocks` | Videos on Enterprises, Social Impact, Covid-19 |
| Media gallery manager (`/media-gallery`), Media events (+ images) | `media-events`, `media-event-images`, `gallery-images` | Media → Events, Gallery |
| Media coverage links, Documents | `media-coverage-links`, `documents` | Media → Coverage, Documents |
| Central media library (`/media-library`) | (all image fields) | Removed. Photos are chosen in the field that shows them, with size checks and alt text there |
| Navbar menu links (`/resources/nav-items`) | `nav-items` | Header & footer → Navigation |
| Site settings (`/site-settings`) | `site-settings` | Header & footer → Social links, Logos; Contact → Details |
| Contact messages (`/contact-messages`) | `contact-messages` | Messages (publishers and admins only) |
| — (new) | `auth/users/` | Users (admins only) |
| — (new) | `cms/publish`, snapshots | Review & publish, Publish history |
