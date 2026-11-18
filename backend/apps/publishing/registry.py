"""Section registry (contract §2): page -> sections -> resource + editable fields.

One Python structure drives the CMS page editor, MCP tools, prerender paths, snapshot collections and the
changes/discard item ids. `export_registry()` enriches each field from the model (label, max length, required,
choices) so this file only states what the model can't.

Item ids: `<section id>.<resource>:<pk>` (e.g. `home.hero.hero-slides:7`); never positional.
Extensions over contract §2 (reported to the lead): field type `file` (PDF/video), `options_from` on select
fields that pick a parent row, `warn_width` on images, `filter`/`defaults` on page-scoped sections, and a
top-level `globals` list for site-wide sections (header, footer, nav) that belong to no single page.
"""
from dataclasses import dataclass
from functools import cache
from importlib import import_module

from django.apps import apps as django_apps

from .pages import PAGES

FIELD_TYPES = {"text", "textarea", "richtext", "image", "url", "date", "number", "select", "boolean", "file"}
HERO_MIN_WIDTH = 1600
WARN_WIDTH = 1200


@dataclass(frozen=True)
class Resource:
    name: str
    model: str  # "app_label.Model"
    serializer: str  # dotted path of the existing DRF list serializer
    kind: str = "collection"  # or "singleton"
    parents: tuple = ()  # FK fields (to visible-filterable parents) whose hiding hides this row too

    @property
    def model_class(self):
        return django_apps.get_model(self.model)

    @property
    def serializer_class(self):
        module, _, cls = self.serializer.rpartition(".")
        return getattr(import_module(module), cls)

    @property
    def has_visibility(self):
        return any(f.name == "is_published" for f in self.model_class._meta.concrete_fields)


def _r(name, model, serializer, **kw):
    return name, Resource(name, model, serializer, **kw)


RESOURCES = dict([
    _r("site-settings", "core.SiteSettings", "apps.core.serializers.SiteSettingsSerializer", kind="singleton"),
    _r("about-page", "core.AboutPage", "apps.core.serializers.AboutPageSerializer", kind="singleton"),
    _r("home-page", "core.HomePage", "apps.core.serializers.HomePageSerializer", kind="singleton"),
    _r("nav-items", "core.NavItem", "apps.core.serializers.NavItemSerializer"),
    _r("news-items", "core.NewsItem", "apps.core.serializers.NewsItemSerializer"),
    _r("focus-areas", "core.FocusArea", "apps.core.serializers.FocusAreaSerializer"),
    _r("objective-rows", "core.ObjectiveRow", "apps.core.serializers.ObjectiveRowSerializer"),
    _r("timeline-entries", "core.TimelineEntry", "apps.core.serializers.TimelineEntrySerializer"),
    _r("hero-slides", "carousel.HeroSlide", "apps.carousel.serializers.HeroSlideSerializer"),
    _r("project-slides", "carousel.ProjectSlide", "apps.carousel.serializers.ProjectSlideSerializer"),
    _r("team-categories", "team.TeamCategory", "apps.team.serializers.TeamCategorySerializer"),
    _r("team-members", "team.TeamMember", "apps.team.serializers.TeamMemberSerializer", parents=("category",)),
    _r("equipment", "facilities.Equipment", "apps.facilities.serializers.EquipmentSerializer"),
    _r("services", "services.Service", "apps.services.serializers.ServiceSerializer"),
    _r("innovations", "innovations.Innovation", "apps.innovations.serializers.InnovationSerializer"),
    _r("innovation-images", "innovations.InnovationImage", "apps.innovations.serializers.InnovationImageSerializer",
       parents=("innovation",)),
    _r("products", "products.Product", "apps.products.serializers.ProductSerializer"),
    _r("product-images", "products.ProductImage", "apps.products.serializers.ProductImageSerializer", parents=("product",)),
    _r("product-partners", "products.ProductPartner", "apps.products.serializers.ProductPartnerSerializer",
       parents=("product",)),
    _r("enterprises", "enterprises.Enterprise", "apps.enterprises.serializers.EnterpriseSerializer"),
    _r("media-events", "media_gallery.MediaEvent", "apps.media_gallery.serializers.MediaEventSerializer"),
    _r("media-event-images", "media_gallery.MediaEventImage", "apps.media_gallery.serializers.MediaEventImageSerializer",
       parents=("event",)),
    _r("media-coverage-links", "media_gallery.MediaCoverageLink",
       "apps.media_gallery.serializers.MediaCoverageLinkSerializer"),
    _r("gallery-images", "media_gallery.GalleryImage", "apps.media_gallery.serializers.GalleryImageSerializer"),
    _r("image-grid-blocks", "common.ImageGridBlock", "apps.common.serializers.ImageGridBlockSerializer"),
    _r("image-grid-items", "common.ImageGridItem", "apps.common.serializers.ImageGridItemSerializer", parents=("block",)),
    _r("video-blocks", "common.VideoBlock", "apps.common.serializers.VideoBlockSerializer"),
    _r("documents", "common.Document", "apps.common.serializers.DocumentSerializer"),
])
SINGLETONS = [n for n, r in RESOURCES.items() if r.kind == "singleton"]
COLLECTIONS = [n for n, r in RESOURCES.items() if r.kind == "collection"]
# FK field -> resource it points at (used to resolve page-scoped sections for rows that only exist in a snapshot).
FK_RESOURCES = {
    ("team-members", "category"): "team-categories",
    ("innovation-images", "innovation"): "innovations",
    ("product-images", "product"): "products",
    ("product-partners", "product"): "products",
    ("media-event-images", "event"): "media-events",
    ("image-grid-items", "block"): "image-grid-blocks",
}


# ---- field helpers ------------------------------------------------------------------------------------------
def f(name, type="text", **extra):
    assert type in FIELD_TYPES, type
    return {"name": name, "type": type, **extra}


def img(name, min_width=None, alt_field=None, required=None):
    d = f(name, "image")
    if min_width:
        d["min_width"] = min_width
    else:
        d["warn_width"] = WARN_WIDTH
    if alt_field:
        d["alt_field"] = alt_field
    if required is not None:
        d["required"] = required
    return d


VISIBLE = f("is_published", "boolean", label="Visible on the site")


def sec(id, label, resource, fields, **extra):
    return {"id": id, "label": label, "kind": RESOURCES[resource].kind, "resource": resource, "fields": fields, **extra}


def grid_sections(page):
    """Image grids + videos for the pages that use ImageGridBlock / VideoBlock (filtered by `page`)."""
    return [
        sec(f"{page}.grids", "Image grid sections", "image-grid-blocks",
            [f("section_title"), f("anchor_slug"), f("intro", "textarea"), VISIBLE],
            filter={"page": page}, defaults={"page": page}),
        sec(f"{page}.grid-images", "Image grid photos", "image-grid-items",
            [f("block", "select", options_from="image-grid-blocks"), img("image", alt_field="caption", required=True),
             f("caption"), VISIBLE],
            filter={"block__page": page}),
    ]


def video_section(page):
    return sec(f"{page}.videos", "Videos", "video-blocks",
               [f("title"), f("youtube_url", "url"), f("video_file", "file"), VISIBLE],
               filter={"page": page}, defaults={"page": page})


SECTIONS_BY_PAGE = {
    "home": [
        sec("home.hero", "Hero", "hero-slides", [
            img("image", min_width=HERO_MIN_WIDTH, alt_field="alt_text", required=True),
            f("alt_text", label="Photo description (alt text)", required=True),
            f("eyebrow"), f("heading"), f("highlight_heading"), f("heading_end"), f("description", "textarea"),
            f("primary_button_label"), f("primary_button_link", "url"),
            f("secondary_button_label"), f("secondary_button_link", "url"),
            f("image_position", "select"), VISIBLE]),
        sec("home.news", "News ticker", "news-items", [f("text", "textarea"), f("link_url", "url"), VISIBLE]),
        sec("home.objective", "Objective", "home-page", [f("objective_text", "textarea")]),
        sec("home.enterprises", "Enterprises engagement", "home-page", [
            f("enterprises_text", "textarea"), img("enterprises_image_1"), img("enterprises_image_2"),
            img("msme_map_image", alt_field="msme_caption"), f("msme_caption")]),
        sec("home.women", "Women empowerment", "home-page", [
            f("women_text_1", "textarea"), img("women_image_1"), img("women_image_2"), f("women_text_2", "textarea")]),
        sec("home.location", "Location", "home-page", [
            f("location_address"), f("location_description", "textarea"), img("office_image")]),
        sec("home.facilities", "Facility cards", "home-page", [
            x for i in (1, 2, 3) for x in (f(f"facility_card_{i}_title"),
                                           img(f"facility_card_{i}_image", alt_field=f"facility_card_{i}_title"),
                                           f(f"facility_card_{i}_link", "url"))]),
        sec("home.videos", "Videos", "home-page", [f("chintan_shivir_youtube_id"), f("viksit_bharat_youtube_id")]),
        sec("home.membership", "Annual membership", "home-page", [f("membership_heading"), f("membership_pdf", "file")]),
    ],
    "about": [
        sec("about.intro", "About CRTDH", "about-page", [f("intro", "textarea"), f("mission_vision", "textarea")]),
        sec("about.focus-intro", "Focus areas intro", "about-page", [f("focus_intro", "textarea")]),
        sec("about.focus-areas", "Focus areas", "focus-areas", [f("title"), f("color"), VISIBLE]),
        sec("about.objectives", "Objectives table", "objective-rows",
            [f("category"), f("task", "textarea"), f("outcome", "textarea"), VISIBLE]),
        sec("about.timeline", "Timeline", "timeline-entries", [f("year"), f("title"), img("image", alt_field="title"), VISIBLE]),
        sec("about.ecosystem", "Ecosystem", "about-page", [f("ecosystem_heading"), img("ecosystem_image", alt_field="ecosystem_heading")]),
        sec("about.pi-desk", "From the PI's desk", "about-page", [img("pi_desk_image"), f("pi_desk_document", "file")]),
        sec("about.partners", "DSIR and IIT Kharagpur", "about-page", [f("dsir_about", "textarea"), f("iitkgp_about", "textarea")]),
    ],
    "team": [
        sec("team.categories", "Team groups", "team-categories", [f("name"), VISIBLE]),
        sec("team.members", "Team members", "team-members", [
            f("category", "select", options_from="team-categories"), f("name"), img("photo", alt_field="name"),
            f("designation"), f("institution"), f("description", "textarea"), VISIBLE]),
    ],
    "innovations": [
        sec("innovations.list", "Innovations", "innovations",
            [f("title"), f("body", "richtext"), f("video_url", "url"), VISIBLE]),
        sec("innovations.images", "Innovation photos", "innovation-images", [
            f("innovation", "select", options_from="innovations"), img("image", alt_field="caption", required=True),
            f("caption"), VISIBLE]),
        sec("innovations.projects", "Project slides", "project-slides",
            [img("image", alt_field="title", required=True), f("title"), VISIBLE]),
    ],
    "facilities": [
        sec("facilities.equipment", "Equipment", "equipment", [f("name"), img("image", alt_field="name"), VISIBLE]),
        *grid_sections("facilities"),
    ],
    "services": [
        sec("services.list", "Services", "services", [f("title"), img("image", alt_field="title"), VISIBLE]),
    ],
    "product": [
        sec("product.list", "Products", "products", [f("name"), VISIBLE]),
        sec("product.images", "Product photos", "product-images", [
            f("product", "select", options_from="products"), img("image", required=True), VISIBLE]),
        sec("product.partners", "Product partners", "product-partners", [
            f("product", "select", options_from="products"), f("name"), img("logo", alt_field="name"), VISIBLE]),
    ],
    "enterprises": [
        sec("enterprises.list", "Enterprises", "enterprises", [f("name"), f("subtitle"), img("logo", alt_field="name"), VISIBLE]),
        *grid_sections("enterprises"),
        video_section("enterprises"),
    ],
    "social-impact": [*grid_sections("social-impact"), video_section("social-impact")],
    "covid-19": [*grid_sections("covid-19"), video_section("covid-19")],
    "media": [
        sec("media.events", "Events", "media-events", [
            f("title"), f("slug"), f("description", "textarea"), f("event_date", "date"), f("category", "select"), VISIBLE]),
        sec("media.event-images", "Event photos", "media-event-images", [
            f("event", "select", options_from="media-events"), img("image", alt_field="caption", required=True),
            f("caption"), VISIBLE]),
        sec("media.coverage", "Press coverage links", "media-coverage-links", [f("title"), f("url", "url"), VISIBLE]),
        sec("media.gallery", "Photo gallery", "gallery-images", [img("image", alt_field="caption", required=True),
                                                                 f("caption"), VISIBLE]),
    ],
    "contact": [
        sec("contact.details", "Contact details", "site-settings", [
            f("address", "textarea"), f("phone_primary"), f("phone_secondary"), f("email_primary"),
            f("email_secondary"), f("map_embed_url", "url")]),
    ],
}

GLOBALS = [
    sec("site.header", "Header logos", "site-settings", [img("site_logo"), img("logo_left"), img("logo_right")]),
    sec("site.social", "Social links", "site-settings",
        [f("facebook_url", "url"), f("linkedin_url", "url"), f("instagram_url", "url"), f("twitter_url", "url")]),
    sec("site.nav", "Navigation", "nav-items", [f("label"), f("url"), f("in_more", "boolean"), VISIBLE]),
    sec("site.documents", "Documents", "documents", [f("title"), f("file", "file"), f("category", "select"), VISIBLE]),
]

REGISTRY = {
    "pages": [{"id": pid, "path": path, "title": title, "sections": SECTIONS_BY_PAGE[pid]} for pid, path, title in PAGES],
    "globals": GLOBALS,
}


# ---- lookups ------------------------------------------------------------------------------------------------
def all_sections():
    for page in REGISTRY["pages"]:
        for s in page["sections"]:
            yield page["id"], s
    for s in REGISTRY["globals"]:
        yield "site", s


@cache
def section_index():
    return {s["id"]: (page_id, s) for page_id, s in all_sections()}


def get_page(page_id):
    return next((p for p in REGISTRY["pages"] if p["id"] == page_id), None)


def sections_for_resource(resource):
    return [(page_id, s) for page_id, s in all_sections() if s["resource"] == resource]


def _value(target, path, resource, lookup):
    """Follow `a__b` through a model instance or a snapshot row dict (FKs resolved with `lookup`)."""
    parts = path.split("__")
    cur, cur_resource = target, resource
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if isinstance(cur, dict):
            val = cur.get(part)
            if not last:
                cur_resource = FK_RESOURCES[(cur_resource, part)]
                val = lookup(cur_resource, val) if lookup else None
        else:
            val = getattr(cur, part, None)
            if not last and val is not None:
                cur_resource = FK_RESOURCES.get((cur_resource, part))
        if val is None:
            return None
        cur = val
    return cur


def section_for(resource, target=None, lookup=None, field=None):
    """The section that owns a row (collections) or a field (singletons)."""
    candidates = sections_for_resource(resource)
    if RESOURCES[resource].kind == "singleton":
        if field:
            for page_id, s in candidates:
                if any(fd["name"] == field for fd in s["fields"]):
                    return page_id, s
        return candidates[0]
    for page_id, s in candidates:
        flt = s.get("filter")
        if not flt or target is None:
            if not flt:
                return page_id, s
            continue
        if all(_value(target, k, resource, lookup) == v for k, v in flt.items()):
            return page_id, s
    return candidates[0]


def item_id(resource, pk, target=None, lookup=None, field=None):
    _page, s = section_for(resource, target, lookup, field)
    return f"{s['id']}.{resource}:{pk}"


def parse_item_id(value):
    """`home.hero.hero-slides:7` -> (section_id, resource, pk). Raises ValueError."""
    head, sep, pk = (value or "").rpartition(":")
    if not sep:
        raise ValueError("item id must look like <section>.<resource>:<pk>")
    section_id, dot, resource = head.rpartition(".")
    if not dot or resource not in RESOURCES or section_id not in section_index():
        raise ValueError(f"unknown item id {value!r}")
    if section_index()[section_id][1]["resource"] != resource:
        raise ValueError(f"section {section_id} does not hold {resource}")
    try:
        pk = int(pk)
    except ValueError:
        raise ValueError(f"bad pk in {value!r}") from None
    return section_id, resource, pk


# ---- export ---------------------------------------------------------------------------------------------------
def _enrich_field(model, fd):
    out = dict(fd)
    try:
        mf = model._meta.get_field(fd["name"])
    except Exception:  # noqa: BLE001
        return out
    out.setdefault("label", str(mf.verbose_name).capitalize())
    if getattr(mf, "max_length", None) and fd["type"] in ("text", "textarea", "url"):
        out.setdefault("max", mf.max_length)
    if fd["type"] != "boolean":
        out.setdefault("required", not (mf.blank or mf.null or mf.has_default()))
    if mf.choices and fd["type"] == "select":
        out["options"] = [{"value": v, "label": str(lbl)} for v, lbl in mf.choices]
    if mf.help_text:
        out.setdefault("help", str(mf.help_text))
    return out


def export_registry():
    """The registry as JSON-ready data with model-derived field details (embedded in every snapshot)."""

    def section(s):
        model = RESOURCES[s["resource"]].model_class
        return {**s, "fields": [_enrich_field(model, fd) for fd in s["fields"]]}

    return {
        "pages": [{**p, "sections": [section(s) for s in p["sections"]]} for p in REGISTRY["pages"]],
        "globals": [section(s) for s in REGISTRY["globals"]],
    }


def preview_url(item_id_value):
    from django.conf import settings

    section_id, _resource, _pk = parse_item_id(item_id_value)
    page_id = section_index()[section_id][0]
    return f"{settings.CMS_PUBLIC_URL.rstrip('/')}/pages/{page_id}?item={item_id_value}"
