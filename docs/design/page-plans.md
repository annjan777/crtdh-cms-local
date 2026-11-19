# CRTDH v3 — per-page layout plans (WS2.11)

Companion to `frontend/DESIGN.md`. Each plan: the page's one job, its primary action, sections top to bottom (component classes), the content each shows (snapshot resource → field), phone behaviour, and what is hidden when data is empty. "Now" = what the v3/frontend build renders today; **Change** = a jsx change the design lane recommends (styles alone cannot do it).

Shared on every page: `.site-header` (wordmark, About · Our work · Impact · News, Contact action) → page → `.site-footer`. Nav labels come from `nav-items`; the grouping is a design decision pending the content owner's final labels (open item in PLAN Pass 7).

Patterns: **P** persuasive (Home only) · **L** listing (filter/index row + grid of real items) · **D** detail (reading column + facts/picture side) · **F** form.

---

## Home `/` — P
**Job:** in five seconds, say who CRTDH is and that partners can work with it. **Primary action:** Work with CRTDH → /services.

1. **Hero** `.hero.on-navy` + `.hero__prints` — `hero-slides` (first 4 published; slide 1 LCP): `heading` as H1, `description` as the line, two actions (primary Work with CRTDH, secondary See our innovations). Next-slide print + counter + prev/next/pause. `eyebrow`, `highlight_heading`, `heading_end` not rendered. Phone: photo 4:5 full width on top, controls row, then text; next-slide print hidden. Empty: no slides → text column alone on navy.
2. **Who builds with us** `.section.proof` + `.names` — `enterprises.name` (28) in two text columns; `products` + `product-partners` as a `dl`; link All enterprises. Phone: one column. Empty: no enterprises → section hidden; no products → `dl` hidden.
3. **Devices from the lab bench** `.section--surface.work` + `.work__grid` — heading cell + first 6 `innovations` that have an image (`images[0]`), white 4:3 mats, link All N innovations. Phone: heading, wide tile, then two columns. Empty: fewer than 6 → grid fills in order; none → hidden.
4. **From prototype to production** `.section.manufacture` — `home-page.enterprises_text` + `enterprises_image_1/2` (a bottom-aligned pair) + actions; then **Facilities at the centre** `.facility-list` text tiles from `facility_card_1..3_title/link`. Phone: text, pair, tiles stacked. Empty: images missing → pair hidden; card without title → dropped.
5. **Healthcare that reaches the village** `.section--navy.community` — `women_text_1`, `women_image_1/2` (overlapping pair), secondary action Read about our social impact. Empty: no text → section hidden.
6. **News from the centre** `.section.news` + `.rows` — `news-items` (6) as row links, `documents` (newsletters, membership) as PDF rows, one photograph, two videos (`chintan_shivir_youtube_id`, `viksit_bharat_youtube_id`). Empty: no news and no documents → section hidden; each video hidden if its id is blank.
7. **Visit the centre** `.section--surface.visit` — `location_description`, `site-settings.address`, email, phone, directions, membership PDF (`membership_heading`, `membership_pdf`). Photo slot hidden until a real photograph exists (content-gaps).

**Change (jsx):** WS2.2 asks for a **proof strip of figures with sources** (devices in use, people screened, clinics). No such figures exist in the CMS; until they do, "Who builds with us" carries proof. Add a `home-page.figures` list (value, label, source) when the owner supplies them.

## About `/about` — D
**Job:** explain what the centre is, who funds it and what it is for. **Primary action:** none on the page; footer contact.

1. `.banner` — "About CRTDH" + intro.
2. **The CRTDH programme** `.split` — `about-page.intro` (prose) + `ecosystem_image` with `ecosystem_heading` as caption.
3. **Mission and vision** `.section--surface` — `mission_vision`. **Change:** today the right half of this band is empty; set it as `.split` with the `focus-areas` list from section 4 in the side, or set the statement as a 28 px Fraunces paragraph across 8 columns.
4. **Where we work** `.grid12` `.col-head` + `.names--focus` — `focus_intro` + `focus-areas.title` (7). Focus-area `color` is not used (it would be a rainbow).
5. **How CRTDH supports MSMEs** `.section--surface` + `.table` — `objective-rows` grouped by `category` (task, outcome). Phone: table scrolls horizontally inside `.table-wrap`. Empty: hidden.
6. **The healthcare ecosystem at IIT Kharagpur** `.timeline` (`<ol>`) — `timeline-entries` year, title, image 3:2.
7. **From the Principal Investigator's desk** `.split--reverse` — `pi_desk_image`, `pi_desk_document`. **Gap:** no message text (`pi_desk_document` is null), so the section is a heading and a poster. Hide the section until a message exists, or render the poster as a figure under section 2.
8. **DSIR, Government of India / IIT Kharagpur** `.two-col` — `dsir_about`, `iitkgp_about`.

## Team `/team` — L
**Job:** show who runs the centre. **Primary action:** Contact CRTDH (closing band).

1. `.banner` — "Our team" + intro.
2. One `.team__group` per `team-categories` (in `order`) with members: H2 category (28 px navy) left 3 cols, `.people` 4:5 portraits right; a group of one sets portrait beside name. Fields: `photo`, `name`, `designation` (teal role line), `institution`, `description`. Phone: category heading above, two-column people grid. Empty: category with no published members hidden; member without photo → surface 4:5 block (no initials, no icon).
3. **Work with the team** `.section--surface.closing` — primary Contact CRTDH.

## Innovations `/innovations` — L/D
**Job:** let a partner find a device and judge its readiness. **Primary action:** none per item; closing contact recommended (**Change:** add the `.closing` band "Licence or co-develop a technology" → /contact).

1. `.banner` + `.jump` — "Innovations" + intro; index of all 13 `innovations.title` in two columns.
2. **Project spotlight** `.section--surface` + `.spotlight` — `project-slides` (4: Mobile App, Paper Strip, Detection Box, Smartphone based analysis). Empty: hidden.
3. **All innovations** `.articles` > `.article` — H2 title, `body` (rich text: p, h3, ul, ol), `video_url` poster; `images` (max 4) in `.article__media`, right, sticky, white 4:3 mats; captions shown when more than one image. Text-only items run full measure. Phone: text then figures. Empty: whole section hidden.

## Facilities `/facilities` — L
**Job:** show what equipment and plant a partner can use. **Primary action:** **Change:** closing band "Book a facility" → /contact.

1. `.banner`.
2. **Laboratory and testing equipment** `.tiles` — `equipment` (21): image 3:2 + name; items without image become text tiles (Fraunces 22). Phone: 2 columns, 1 under 480 px.
3. **Manufacturing plants and demonstration units** `.section--surface` + gallery — `image-grid-blocks` where `page = facilities` (anchor `manufacturingplants`) and its `image-grid-items`. Empty: hidden.

## Services `/services` — L
**Job:** say what the centre offers MSMEs and startups. **Primary action:** Ask about a service (banner).

1. `.banner` + `.actions` (primary "Ask about a service" → /contact, text link to the membership PDF).
2. `.services__list` — `services` (6) title + 1:1 image, three columns with the middle column dropped 48 px. **Gap:** services have no description field; each needs one sentence (content-gaps).

## Product `/product` — D (repeated)
**Job:** show which devices reached the market and through whom. **Primary action:** none; footer contact.

1. `.banner`.
2. `.products__list` > `.product` — `products.name` (H2), `product-images` (2, white mats), "Commercialisation partners" + `product-partners` (logo + name). Phone: images then text. Empty: hidden. **Gap:** no description or status per product.

## Enterprises `/enterprises` — L
**Job:** show the MSME cluster the centre supports. **Primary action:** Annual membership (recommended in the closing band).

1. `.banner`.
2. **Enterprise engagement** `.split` — `home-page.enterprises_text` + `msme_map_image` with `msme_caption`.
3. **The enterprise cluster** `.section--surface` + `.logos` — `enterprises` (28) logo (or name in Fraunces when no logo), `subtitle`. Phone: 2 columns.
4. **Demonstration and training of MSMEs** — image-grid block `page = enterprises`. Empty: hidden.
5. **Enterprise stories** `.videos`. Empty: hidden.

## Social impact `/social-impact` — D
**Job:** show the community health work. **Primary action:** none; Media for photographs.

1. `.banner--print` "Social impact" with `women_image_1`.
2. **E-health clinics and local livelihoods** `.split` — `women_text_1` + `women_text_2`, `women_image_2` (4:5) in the side.
3. **Community outreach** `.section--surface` — image-grid block `page = social-impact` (12 items, captions). Empty: hidden.
4. **Community stories** `.videos` — `video-blocks` where `page = social-impact`. Empty: hidden (none today).

## Covid-19 `/covid-19` — D
**Job:** record the centre's pandemic response (COVIRAP, PINAT, Covicube). **Primary action:** See the COVIRAP innovation → /innovations#… (recommended).

1. `.banner` "Covid-19 response".
2. **Combating the pandemic** — image-grid block `page = covid-19` intro as prose.
3. **In the field** `.section--surface` gallery — its items.
4. **Response in action** `.videos` — `video-blocks` (2: CRTDH Covid-19 response, PINAT diagnostic platform).

## Media `/media` — L
**Job:** show the centre's activity as photographs and press. **Primary action:** none.

1. `.banner` + `.jump` — event names, Press coverage, Newsletters.
2. One `.section.event` per `media-events` (alternating paper/surface): H2 `title`, `description`, `.gallery__grid` (lead photo 2 x 2, first 6, "Show all N photos"). **Gap:** `event_date` is empty on all 8 events; dates belong beside each title once filled.
3. **Press coverage** `.rows` — `media-coverage-links`. **Gap:** every `title` is the raw URL; each needs "Headline — Publication, date".
4. **Newsletters** `.rows` — `documents` category newsletter.
5. **More from CRTDH** gallery — `gallery-images`. Empty: hidden.

## Contact `/contact` — F
**Job:** let a partner write to the centre. **Primary action:** Send message.

1. `.banner`.
2. `.contact__grid` — form (name, email, phone optional, message; blur validation, sending, sent, Turnstile, rate-limit and `mailto:` fallback states) + **The office** `.facts` (address, phone, emails) + map iframe 4:3. Phone: form first, then facts and map.
3. **How we use contact messages** `.section--surface` prose (privacy notice).

## 404
**Job:** get a lost visitor back. **Primary action:** Go to the home page.

`.notfound` `.grid12`: H1 "This page is not on the site", one sentence, search field, primary button; right: `.rows` of the main pages with one-line descriptions. Phone: stacked.
