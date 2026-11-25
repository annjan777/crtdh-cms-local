"""Section registry (contract §2): page -> sections -> resource + editable fields.

One Python structure drives the CMS page editor, MCP tools, prerender paths, snapshot collections and the
changes/discard item ids. `export_registry()` enriches each field from the model (label, max length, required,
choices) so this file only states what the model can't.

Item ids: `<section id>.<resource>:<pk>` (e.g. `home.hero.hero-slides:7`); never positional.
Section data lives in registry_data.py (ported from the admin lane's mock so ids/labels match). Addendum A2
extras: description, item_label, item_noun, add_label, filter{page}, children[{resource,parent_field,label,fields}],
field label/help, image alt_field/position_field/min_width/warn_width, select choices/choices_resource.
Further extensions: field type `file` (PDF/video) and a top-level `globals` list (site-wide sections: menu,
social links, logos) served by GET /cms/pages/site/.
"""
from dataclasses import dataclass
from functools import cache
from importlib import import_module

from django.apps import apps as django_apps

from .pages import PAGES
from .registry_data import GLOBAL_SECTIONS, PAGE_SECTIONS

FIELD_TYPES = {"text", "textarea", "richtext", "image", "url", "date", "number", "select", "boolean", "file"}
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
    _r("page-heroes", "common.PageHero", "apps.common.serializers.PageHeroSerializer"),
    _r("research-stories", "common.ResearchStory", "apps.common.serializers.ResearchStorySerializer"),
    _r("impact-figures", "common.ImpactFigure", "apps.common.serializers.ImpactFigureSerializer"),
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


REGISTRY = {
    "pages": [{"id": pid, "path": path, "title": title, "sections": PAGE_SECTIONS[pid]} for pid, path, title in PAGES],
    "globals": GLOBAL_SECTIONS,
}
GLOBALS = GLOBAL_SECTIONS


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


def _child_view(section, child):
    """A child list (e.g. innovation photos) seen as a section of its own: same id as its parent section."""
    flt = {f"{child['parent_field']}__{k}": v for k, v in (section.get("filter") or {}).items()}
    return {**child, "id": section["id"], "kind": "collection", "parent_section": section["id"],
            "filter": flt or None}


@cache
def all_views():
    """Every (page_id, section view): top-level sections plus their child lists (see _child_view)."""
    return _views()


@cache
def _views():
    out = []
    for page_id, s in all_sections():
        out.append((page_id, s))
        for child in s.get("children") or []:
            out.append((page_id, _child_view(s, child)))
    return out


def sections_for_resource(resource):
    """(page_id, section view) pairs holding a resource; child lists come back as views with their own fields."""
    return [(page_id, s) for page_id, s in _views() if s["resource"] == resource]


def section_view(section_id, resource):
    return next((s for _p, s in _views() if s["id"] == section_id and s["resource"] == resource), None)


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
    """(page_id, section view) that owns a row (collections) or a field (singletons)."""
    candidates = sections_for_resource(resource)
    if not candidates:
        raise KeyError(resource)
    if RESOURCES[resource].kind == "singleton":
        if field:
            for page_id, s in candidates:
                if field in editable_fields(s) - {"is_published", "order"}:
                    return page_id, s
        return candidates[0]
    for page_id, s in candidates:
        flt = s.get("filter")
        if not flt:
            return page_id, s
        if target is not None and all(_value(target, k, resource, lookup) == v for k, v in flt.items()):
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
    if section_view(section_id, resource) is None:
        raise ValueError(f"section {section_id} does not hold {resource}")
    try:
        pk = int(pk)
    except ValueError:
        raise ValueError(f"bad pk in {value!r}") from None
    return section_id, resource, pk


def view_for_item(item_id_value):
    """Parse an item id -> (page_id, section view, resource, pk). Raises ValueError."""
    section_id, resource, pk = parse_item_id(item_id_value)
    return section_index()[section_id][0], section_view(section_id, resource), resource, pk


def editable_fields(section):
    """Field names a section (view) may write: its fields, their alt/position fields, visibility and order."""
    names = {"is_published", "order"}
    for fd in section["fields"]:
        names.add(fd["name"])
        for extra in ("alt_field", "position_field"):
            if fd.get(extra):
                names.add(fd[extra])
    if section.get("parent_field"):
        names.add(section["parent_field"])
    return names


def field_labels(section):
    """{field name: human label} for a section view, including alt/position fields (review screen, audit)."""
    out = {"is_published": "Visible on the site", "order": "Position"}
    for fd in section["fields"]:
        label = fd.get("label") or fd["name"].replace("_", " ").capitalize()
        out[fd["name"]] = label
        if fd.get("alt_field"):
            out[fd["alt_field"]] = f"{label}: description"
        if fd.get("position_field"):
            out[fd["position_field"]] = f"{label}: focus point"
    if section.get("parent_field"):
        out.setdefault(section["parent_field"], section["parent_field"].replace("_", " ").capitalize())
    return out


def min_widths():
    """{"app_label.model.field": min_width} for backend-security's apps.common.fields.MIN_WIDTHS."""
    out = {}
    for _p, s in _views():
        model = RESOURCES[s["resource"]].model_class
        for fd in s["fields"]:
            if fd["type"] == "image" and fd.get("min_width"):
                key = f"{model._meta.app_label}.{model._meta.model_name}.{fd['name']}"
                out[key] = max(out.get(key, 0), fd["min_width"])
    return out


# ---- export ---------------------------------------------------------------------------------------------------
def _enrich_field(model, fd):
    out = dict(fd)
    try:
        mf = model._meta.get_field(fd["name"])
    except Exception:  # noqa: BLE001
        return out
    out.setdefault("label", str(mf.verbose_name).capitalize())
    if getattr(mf, "max_length", None) and fd["type"] in ("text", "textarea", "url"):
        out["max"] = min(out.get("max", mf.max_length), mf.max_length)
    if fd["type"] != "boolean":
        out.setdefault("required", not (mf.blank or mf.null or mf.has_default()))
    if mf.choices and fd["type"] == "select" and not all(isinstance(c, str) for c in out.get("choices") or [{}]):
        out["choices"] = [{"value": v, "label": str(lbl)} for v, lbl in mf.choices]
    if fd["type"] == "image" and not fd.get("min_width"):
        out.setdefault("warn_width", WARN_WIDTH)
    if mf.help_text:
        out.setdefault("help", str(mf.help_text))
    return out


def _export_section(s):
    model = RESOURCES[s["resource"]].model_class
    out = {**s, "fields": [_enrich_field(model, fd) for fd in s["fields"]]}
    if s.get("children"):
        out["children"] = [_export_section(c) for c in s["children"]]
    return out


def export_registry():
    """The registry as JSON-ready data with model-derived field details (embedded in every snapshot)."""
    return {
        "pages": [{**p, "sections": [_export_section(s) for s in p["sections"]]} for p in REGISTRY["pages"]],
        "globals": [_export_section(s) for s in REGISTRY["globals"]],
    }


def preview_url(item_id_value):
    from django.conf import settings

    section_id, _resource, _pk = parse_item_id(item_id_value)
    page_id = section_index()[section_id][0]
    return f"{settings.CMS_PUBLIC_URL.rstrip('/')}/pages/{page_id}?item={item_id_value}"
