---
name: CRTDH public site, v3
direction: "Split stage, institutional"   # design-taste-frontend draw, seed 100803975, palette and type kept from the brand
source_of_truth: frontend/src/site/styles/tokens.css   # values below must match it; change both together
colors:
  paper:        "#f8f7f4"   # page ground, warm off-white (60 %)
  surface:      "#eeece6"   # one tone step: listing cards, alternate bands (30 %)
  surface-2:    "#e4e1d9"   # image placeholder / LQIP fallback, hover step on surface
  ink:          "#17232d"   # running text and headings
  ink-soft:     "#4b5763"   # captions and secondary notes only
  navy:         "#0f4c75"   # brand: H1 on inner pages, links, wordmark
  navy-deep:    "#0b3550"   # hero, community band, footer field
  on-navy:      "#ffffff"
  on-navy-soft: "#c3d3df"
  teal:         "#0a6b6a"   # the one accent on light grounds: primary action, focus ring (10 %)
  teal-hover:   "#085856"
  teal-light:   "#5cc8c4"   # the same accent on navy grounds
  rule:         "#d6d2c8"   # table hairlines, row lists and form borders only
  danger:       "#a4262c"
  success:      "#1d6b3a"
fonts:
  display: { family: "Fraunces (variable, self-hosted)", use: "H1, H2, display figures, footer name", weights: [400, 500, 600] }
  body:    { family: "Open Sans", use: "running text, H3, H4, captions", weights: [400, 600] }
  ui:      { family: "Montserrat", use: "navigation, buttons, text links, form labels, small UI labels", weights: [500, 600] }
type_scale:            # px / line-height
  14: { size: 0.875rem, lh: 1.5,  use: "captions, table heads, footnotes" }
  16: { size: 1rem,     lh: 1.5,  use: "UI labels, buttons, list rows, phone body" }
  17: { size: 1.0625rem, lh: 1.6, use: "body (desktop)" }
  18: { size: 1.125rem, lh: 1.55, use: "lead sentence, H4, H3 on phones" }
  22: { size: 1.375rem, lh: 1.25, use: "H3, tile titles" }
  28: { size: 1.75rem,  lh: 1.15, use: "H2 on phones, article and team-category headings" }
  36: { size: 2.25rem,  lh: 1.12, use: "H2, H1 on phones" }
  48: { size: 3rem,     lh: 1.08, use: "H1 on inner pages" }
  hero: { size: "clamp(2.25rem, 3.9vw, 3.5rem)", lh: 1.06, use: "Home H1 only (28 px on phones)" }
spacing:               # 4 / 8 pt
  s-1: 4px
  s-2: 8px
  s-3: 12px
  s-4: 16px
  s-6: 24px
  s-8: 32px
  s-12: 48px
  s-16: 64px
  s-24: 96px
  s-32: 128px
  section-gap: "clamp(64px, 9vw, 128px)"
frame:
  content-max: 72rem
  margin: "clamp(20px, 5vw, 64px)"
  measure: 68ch
  grid: "12 columns, gap clamp(16px, 2vw, 32px)"
radii:
  radius: 2px          # buttons, inputs, cards: one shape everywhere; images are square
shadows:
  rest: none
  floating: "0 8px 24px rgba(15, 30, 45, 0.07)"   # the nav dropdown only
breakpoints:
  phone: 375           # design width; rules switch below 768
  tablet: 768
  desktop: 1280        # rules switch at 1024 for nav and two-column splits
image_ratios:
  hero: { desktop: "16:9", phone: "4:5" }
  team: "4:5"
  gallery: "3:2"
  work_and_figures: "4:3 on a white mat, object-fit contain (lab figures are never cropped)"
  services: "1:1"
motion:
  fast: 150ms
  base: 200ms
  slow: 300ms
  hero_entrance: "400ms, opacity + 12px rise, 60ms stagger"
  hero_crossfade: "600ms opacity"
  ease_out: "cubic-bezier(0.16, 1, 0.3, 1)"
  ease_in: "cubic-bezier(0.7, 0, 0.84, 0)"
  carousel_hold: "8s, visible Pause, stops on hover/focus/hidden tab, off under reduced motion"
---

# CRTDH design system (v3)

The Common Research & Technology Development Hub on Affordable Healthcare (DSIR, at IIT Kharagpur) is a public, government-funded centre. The site's readers are industry partners, clinicians and health programmes looking to work with the centre, then students and researchers. It must read as **institutional, confident and made by people**: a research centre's own publication, not a startup template.

## Direction

**Split stage, institutional.** Dealt from the design-taste-frontend library and chosen over "the place carries it" (needs 2400 px photography the centre does not have yet; today's hero photos are 500 x 300) and "borrowed category" (wrong register for a public body). The idea: *the centre's own photographs and lab figures sit beside a calm, well-set reading column* — a picture always in view while the reader gets the facts. On Home this is the hero (text left, photograph print right); on Innovations each device's figures stay in view (sticky) beside its text; on detail pages it is the reading column plus facts sidebar.

Surfaces by mode: **Home is persuasive** (one composition per section, no two neighbours alike); **inner pages are for reading** (one column of 65–75 characters, wayfinding, no hero theatre).

## Typography

- Three families, each with one job (owner-approved; this is the maximum):
  - **Fraunces** for H1, H2, display figures and the footer name. Weight 450–500, tracking -0.015 to -0.02em, `text-wrap: balance`, SOFT and WONK axes off.
  - **Open Sans** for everything a visitor reads: body 17 px / 1.6 (16 px on phones), H3 600 at 22 px, H4 600 at 18 px.
  - **Montserrat** only for things a visitor operates: navigation, buttons, text links, form labels, filter/jump links, small UI labels. Never for paragraphs or headings.
- Sizes come only from the scale 14 / 16 / 18 / 22 / 28 / 36 / 48 (body 17). The Home H1 is the one fluid exception.
- Headings never exceed two lines at any width; cut words before shrinking type.
- Left-aligned everywhere. Nothing centred except a lone button inside a dialog.
- No italic, coloured or underlined accent word inside a heading.

## Colour

- 60 / 30 / 10: paper ground, surface and navy fields, teal accent.
- **Teal is the action colour.** It appears on the primary button, the focus ring, the active nav underline and the arrow in row links. Never as a section background, never on headings.
- Navy is the brand: inner-page H1, links, the wordmark, and the three navy fields (Home hero, Home community band, footer).
- Running text is always `--ink` (or white on navy). `--ink-soft` is for captions and notes, never for paragraphs a visitor must read.
- Surfaces separate by a tone step (paper → surface → surface-2), never by a shadow. Hairlines (`--rule`) are allowed only in real tables, row lists, form fields and the header's bottom edge.

### Contrast (WCAG 2.1, all pass AA; most AAA)

| Pair | Ratio |
|---|---|
| ink on paper / surface | 14.91 / 13.52 |
| ink-soft on paper / surface / white | 6.90 / 6.25 / 7.39 |
| navy on paper / surface | 8.48 / 7.69 |
| white on teal (primary button) / teal-hover | 6.32 / 8.27 |
| teal on paper / surface (links on hover, focus ring) | 5.90 / 5.35 |
| white on navy-deep / navy | 12.81 / 9.09 |
| on-navy-soft on navy-deep | 8.36 |
| navy-deep on teal-light (primary button on navy) | 6.41 |
| teal-light focus ring on navy-deep | 6.41 |
| danger on paper | 6.78 |
| success on surface | 5.53 |
| form border #8a8f94 on white (non-text, needs 3:1) | 3.26 |

## Layout and spacing

- One frame: `.wrap` (max 72 rem + margins), equal outer margins `clamp(20px, 5vw, 64px)` at every width.
- 12-column grid inside it. Asymmetry lives inside the grid, never in the frame: an off-centre block is always answered by something on the far side.
- Section rhythm: `--section-gap` (64–128 px) between sections, clearly larger than any gap inside one. Two plain sections in a row share one gap; a coloured band (surface or navy) keeps its own padding.
- Inner spacing uses only the 4/8 scale tokens.
- 375 px: one column, nav becomes a full-screen menu with 48 px rows, listing grids two columns (people, gallery, logos) or one (tiles under 480 px). 768 px: two-column listings. 1024 px: desktop nav and two-column splits. 1280 px and up: content max 72 rem.

## Motion

- One authored moment: the Home hero text rises in once (opacity + 12 px, 400 ms, 60 ms stagger).
- Hero photographs crossfade (600 ms); at most 4 slides, slide 1 is the LCP image; 8 s hold with a visible Pause; stops on hover, focus and a hidden tab; off under reduced motion.
- Feedback only otherwise: colour on hover (150 ms), a 1 px press on buttons, a 4 px arrow nudge on row links, a 3 % image scale on Home work tiles.
- No scroll-reveal on sections. Content is visible without JavaScript.
- Animate `opacity` and `transform` only (plus colour and `flex-grow` on the band strip). `prefers-reduced-motion: reduce` removes all travel and transitions.

## Components (class names in `src/site/styles`)

| Component | Classes | Rule |
|---|---|---|
| Header | `.site-header`, `.wordmark`, `.nav`, `.nav__group`, `.mnav` | Plain paper bar, 72 px, wordmark + four groups + one action. Current page: navy text + 3 px teal underline; in a dropdown, teal text + 600 weight. |
| Page banner (inner pages) | `.banner`, `.banner__inner`, `.banner__intro`, optional `.banner--print` | H1 48 px navy, one intro sentence at 18 px, no photograph unless the page has a real one (`banner--print`). Never a full-bleed image banner on inner pages. |
| Section | `.section`, `.section--surface`, `.section--navy`, `.wrap` | One job per section. Alternate paper and surface; navy at most once per page body (Home only). |
| Section heading | `.section-head` (H2 + at most one sentence) | **No eyebrow.** Context goes into the heading or the sentence (see Banned). |
| Buttons | `.btn.btn--primary`, `.btn.btn--secondary`, `.text-link` | 48 px tall, 2 px radius, Montserrat 600. One primary per view. Secondary is navy outline. Text link is underlined Montserrat, for "see all" and secondary routes. Labels are verbs ("Work with CRTDH", "See the facilities"). |
| Listing card | `.card`, `.tile`, `.logo-card`, `.facility-list__item` | Cards only for listings (equipment, enterprises, facilities). A tone step, no border, no shadow, square image on top or text-only. |
| Person | `.people`, `.person`, `.person__name`, `.person__role`, `.person__inst` | 4:5 portrait, name 18 px 600, role in teal Montserrat 14, institution soft. A group of one sets the portrait beside the name. |
| Figure | `<figure>` + `.img.r-*` + `figcaption` | Square corners, fixed ratio, LQIP colour while loading. Lab figures and screenshots use the white mat (`.img--figure` / contain) so nothing is cropped. Caption 14 px soft, says what the picture is. |
| Facts sidebar | `.split` + `.facts` (dl) | Detail pages: 7/4 split, facts as a `dl` with Montserrat 14 terms and body values. |
| Index / filter row | `.jump` | Plain links to anchors on the page. Innovations sets them in two columns. Not pills, not chips. |
| Rows | `.rows`, `.rows__link` | News, documents, link lists: full-width rows with a hairline and a teal arrow. |
| Gallery | `.gallery__grid`, `.viewer` | 3:2 photographs, 3 columns (2 on phones), native dialog viewer. On Media each event leads with a 2 x 2 photograph. |
| CTA band | `.section--surface` + `.closing` | One H2, one sentence, one primary action. At most one per page, at the end. |
| Footer | `.site-footer` | Navy field; the full centre name returns large in Fraunces; address, phone, email; grouped nav; IIT KGP and DSIR marks; privacy link; "Last updated" stamp. |

## Consistency rules (WS2.11) — every page

1. **Headings.** One H1 per page (48 px inner, fluid on Home; 36 px on phones). H2 36 px (28 phones) Fraunces. H3 22 px Open Sans 600 (18 phones). Never skip a level. Two lines maximum.
2. **Section spacing.** `--section-gap` between sections; `--s-12` between a section heading and its content; `--s-6` between H2 and its prose.
3. **Page banner.** Every inner page opens with `.banner`: H1 + one sentence on paper. No carousel, no background photo, no gradient overlay.
4. **Buttons.** Primary teal fill (teal-light on navy), secondary navy outline, text link underlined. One shape (2 px radius), 48 px tall, verb labels. At most one primary in any viewport.
5. **Cards.** Only for listings. Tone step, no border, no shadow, no icon on top, no rounded corners beyond 2 px.
6. **Image ratios.** Hero 16:9 desktop / 4:5 phone; team 4:5; gallery 3:2; work tiles and innovation figures 4:3 on a white mat; services 1:1. Square corners everywhere.
7. **Links and focus.** Body links navy, underlined, teal on hover. Focus: 3 px teal ring, 2 px offset (teal-light on navy). Targets at least 44 x 44 px.
8. **Fonts.** Fraunces, Open Sans, Montserrat, in the roles above. No other family is loaded. `@fontsource-variable/fraunces` (Fraunces is self-hosted from `src/site/fonts/`) and `lucide-react` are imported nowhere and should be dropped from `package.json`.
9. **Empty data.** A section whose list is empty is not rendered (heading included). Never "No items", never a placeholder image.
10. **Copy.** Sentence case everywhere, including buttons and nav. No ALL CAPS strings from the CMS (render them as written but the CMS should store sentence case).

## Banned (checked in review)

- Gradients of any kind (backgrounds, buttons, text). The only exception is a neutral scrim under text on a photograph.
- Glass / `backdrop-filter`, floating pill navigation.
- Shadows on anything at rest. Only the open nav dropdown floats.
- 4 px (or any) coloured side borders as decoration, including on the current menu item.
- Eyebrow labels: small text above a heading, pill badges, "New ·" chips, tiny tracked uppercase labels. The hero slide's `eyebrow` field ("DSIR · GOVERNMENT OF INDIA") is not rendered; that fact belongs in the footer and the About page.
- Index numbering (01 / 02 / 03) as decoration. A real `<ol>` where order matters.
- Monospace outside code.
- Icon-topped feature cards and rows of identical icon cards. The facility images on Home are clipart, so they are hidden until real photographs exist.
- Cartoon or stock vector illustration (the "office" illustration on Home is hidden for this reason).
- Emoji, decorative blobs, decorative shapes.
- Autoplaying video; autoplaying carousel faster than 7 s or without a visible pause.

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 19 Nov 2026 | Hero carousel kept, max 4 slides, slide 1 LCP, 8 s with Pause | Gate d3 (owner) |
| 19 Nov 2026 | Fraunces for H1/H2 | Gate d4 (owner); gives the institution a voice Montserrat could not |
| 19 Nov 2026 | Direction "split stage" | Photography is 500 px wide today; a half-width print is honest at that size, a full-bleed one is not |
| 19 Nov 2026 | Three families allowed | Owner-approved; roles kept strict so it reads as one system |
| 19 Nov 2026 | No eyebrows, even though the brief listed "section heading with eyebrow" | Eyebrows are the most common generated-page tell; wayfinding is done by the nav's current state and the H1 |
