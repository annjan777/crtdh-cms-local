# CRTDH v3 — content the owner must supply or correct

Found while planning every page against `team/stub-snapshot.json` (19 Nov 2026). Nothing here is invented on the site; until filled, the section is hidden or shows what exists.

## Photography (blocks "wow"; WS2.6 shot list)
- **Hero:** all slides are 500 x 300 except `banner09` (1040 x 585). Need at least 4 photographs of 2400 px or more (building exterior, lab at work, a device in use, a camp). One slide (`ChatGPT_Image_…png`) is an AI-generated image whose file is missing; it should not be published as a photograph of the centre.
- **Hero slides** carry identical heading/description on all 18 rows; only 4 are shown. Each kept slide needs its own alt text (`alt_text` is absent in the stub).
- **Home facility cards 1–3:** images are clipart icons (conference table, machine, biohazard sign); hidden. Need one photograph each of the conference room, pilot plant and sterile room.
- **Home visit section:** `office.png` is a cartoon illustration; hidden. Need a photograph of the Bioscience Building entrance (Diamond Jubilee Complex).
- **Home enterprise and women-empowerment images:** 500 x 300; replace with 1600 px+.
- **Innovation images:** many are 132 x 107 thumbnails or slide screenshots; each innovation needs one clean product photograph.
- **Team:** portraits vary (450 px to 1199 px, mixed backgrounds). A consistent re-shoot (same backdrop, 4:5) would lift the page most.
- **About, PI desk:** the image is a promotional poster with clipart, not a photograph.

## Text
- **Hero headline:** the H1 is the centre's full name (44 characters), which wraps to three lines at every width; a headline should fit two lines (about 32 characters). Suggested: H1 "Affordable healthcare technology" style line written by the owner, with the full name moved to the supporting sentence or kept in the header/footer. Owner's wording; the design does not invent it.
- **Proof figures (Home, WS2.2):** devices in use, people screened, clinics running, MSMEs trained — each with a source and year. None exist in the CMS.
- **PI's message (About):** `pi_desk_document` is null and there is no message text.
- **Team:** `designation` is empty for all 9 members; `description` empty for all.
- **Services:** the 6 services have titles only; each needs one or two sentences of what it includes.
- **Products:** no description or status (prototype / validated / on sale) for the 5 products.
- **Innovations:** several bodies repeat the title as their only sentence (Testing Blood on a Portable Spinning Disc, COVIRAP, Clinical Algorithm App – Uday, Lipidest). Each needs a two- or three-sentence summary: what it measures, for whom, stage.
- **Media events:** `event_date` is empty on all 8 events; `description` empty on all. "Jio" and "Other Ongoing Activities" need real titles.
- **Press coverage:** every `title` is the raw URL. Needs "Headline — Publication, date".
- **Enterprises:** casing is inconsistent ("SPATIAL KARMA RESOURCES PVT. LTD.", "M/s …", "3d Printing Facilities" in equipment); store names as the companies write them, in sentence or title case.
- **Contact:** `email_secondary` is a personal Gmail address shown publicly on every page footer; confirm it should be public. Social links are all empty (the footer hides them).
- **Contact form reply time** ("we reply within 3 working days") needs the owner's wording.
- **Nav labels:** final public labels and grouping (About · Our work · Impact · News) need the content owner's sign-off.

## Dummy or doubtful values to check
- Hero `eyebrow` "DSIR · GOVERNMENT OF INDIA" is ALL CAPS and not rendered (no eyebrows in v3).
- `focus-areas.color` values (#520000 … #4c5500) are not used; they would make a rainbow.
- Duplicate hero `order` 2 on two rows.
