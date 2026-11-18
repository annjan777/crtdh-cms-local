"""The only module in mcp_server that touches CMS internals.

Every other MCP module calls these functions. Until backend-core merges, they work on the
existing models directly; each `TODO(integration, backend-core)` names the core function to
call instead (names confirmed by backend-core, inbox/mcp.md 19 Nov 21:24Z). Core writes take
`ctx = apps.publishing.audit.WriteContext(user=actor.user, channel="mcp",
connector_session=actor.session_key)` and raise `apps.publishing.errors.CMSError`, whose
`.body` is the §4 dict (map it to errors.CmsError; `errors.as_error_body(exc)` for anything else). Item ids follow contracts §2:
`<section id>.<resource>:<pk>`, e.g. `home.hero.hero-slides:7`.

All functions are synchronous (Django ORM); the tool layer runs them in a worker thread.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.validators import URLValidator
from django.db import models, transaction
from django.utils.text import slugify

from . import _fallback_registry as fallback
from .errors import CmsError
from .fetch import fetch_image_bytes
from .images import process_image
from .models import ConnectorWrite, StagedImage


@dataclass(frozen=True)
class Actor:
    """Who is calling: the CMS user behind the OAuth token and the MCP connector session."""

    user: Any
    session_key: str
    request_id: str


# --------------------------------------------------------------------------- registry
# TODO(integration, backend-core): use apps.publishing.registry — REGISTRY / export_registry()
# for pages+fields (types incl. "file", "options_from", min_width/warn_width, filter/defaults,
# top-level "globals"), get_page(), section_index(), RESOURCES, item_id(), parse_item_id().
def _resource_models() -> dict[str, type[models.Model]]:
    from apps.carousel.models import HeroSlide, ProjectSlide
    from apps.common.models import ImageGridBlock, ImageGridItem, VideoBlock
    from apps.core.models import (
        AboutPage, FocusArea, HomePage, NewsItem, ObjectiveRow, SiteSettings, TimelineEntry,
    )
    from apps.enterprises.models import Enterprise
    from apps.facilities.models import Equipment
    from apps.innovations.models import Innovation, InnovationImage
    from apps.media_gallery.models import GalleryImage, MediaCoverageLink, MediaEvent, MediaEventImage
    from apps.products.models import Product
    from apps.services.models import Service
    from apps.team.models import TeamMember

    return {
        "hero-slides": HeroSlide, "project-slides": ProjectSlide, "news-items": NewsItem,
        "home-page": HomePage, "about-page": AboutPage, "site-settings": SiteSettings,
        "focus-areas": FocusArea, "objective-rows": ObjectiveRow, "timeline-entries": TimelineEntry,
        "team-members": TeamMember, "innovations": Innovation, "innovation-images": InnovationImage,
        "equipment": Equipment, "services": Service, "products": Product, "enterprises": Enterprise,
        "image-grid-blocks": ImageGridBlock, "image-grid-items": ImageGridItem, "video-blocks": VideoBlock,
        "media-events": MediaEvent, "media-event-images": MediaEventImage,
        "media-coverage-links": MediaCoverageLink, "gallery-images": GalleryImage,
    }


_FIELD_TYPES = [
    (models.ImageField, "image"), (models.FileField, None), (models.URLField, "url"),
    (models.DateField, "date"), (models.BooleanField, "boolean"), (models.IntegerField, "number"),
    (models.TextField, "textarea"), (models.CharField, "text"), (models.ForeignKey, "select"),
]


def _model_fields(resource: str, model) -> list[dict]:
    overrides = fallback.FIELD_OVERRIDES.get(resource, {})
    fields = []
    for f in model._meta.concrete_fields:
        if f.name in fallback.HIDDEN_FIELDS or f.primary_key:
            continue
        ftype = next((t for cls, t in _FIELD_TYPES if isinstance(f, cls)), None)
        if ftype is None:
            continue
        if ftype == "text" and (f.name == "url" or f.name.endswith(("_link", "_url"))):
            ftype = "url"  # link fields stored as CharField still get link validation
        spec: dict[str, Any] = {"name": f.name, "type": ftype, "label": str(f.verbose_name).capitalize()}
        if f.choices:
            spec["type"] = "select"
            spec["choices"] = [str(v) for v, _ in f.choices if v != ""]
        if isinstance(f, models.ForeignKey):
            spec["help"] = f"Name of an existing {f.related_model._meta.verbose_name}."
        if getattr(f, "max_length", None) and ftype in ("text", "url"):
            spec["max"] = f.max_length
        if not f.blank and ftype not in ("boolean", "number"):
            spec["required"] = True
        spec.update(overrides.get(f.name, {}))
        fields.append(spec)
    gallery = fallback.GALLERIES.get(resource)
    if gallery:
        fields.append({"name": gallery["name"], "type": "gallery", "label": "Photos",
                       "help": "List of {media_id, caption}. Adds photos to this item."})
    return fields


def registry_pages() -> list[dict]:
    """Pages with sections and field schemas (contracts §2 shape)."""
    resources = _resource_models()
    pages = []
    for page in fallback.PAGES:
        sections = []
        for s in page["sections"]:
            sections.append({**s, "fields": _model_fields(s["resource"], resources[s["resource"]])})
        pages.append({**page, "sections": sections})
    return pages


def page_ids() -> list[str]:
    return [p["id"] for p in fallback.PAGES]


def _page(page_id: str) -> dict:
    for page in registry_pages():
        if page["id"] == page_id:
            return page
    raise CmsError("CMS_NOT_FOUND", f"There is no page called {page_id!r}. Pages: {', '.join(page_ids())}.",
                   fix="Use one of the listed page ids.", field="page")


def _section(section_id: str) -> tuple[dict, dict]:
    for page in registry_pages():
        for s in page["sections"]:
            if s["id"] == section_id:
                return page, s
    raise CmsError("CMS_NOT_FOUND", f"There is no section {section_id!r}.", field="section")


def collection_sections(resource: str) -> list[dict]:
    return [s for p in registry_pages() for s in p["sections"] if s["resource"] == resource]


def make_item_id(section_id: str, resource: str, pk: int) -> str:
    return f"{section_id}.{resource}:{pk}"


def _parse_item_id(item_id: str):
    """-> (page, section, model, obj). Raises CMS_NOT_FOUND."""
    m = re.fullmatch(r"([a-z0-9-]+(?:\.[a-z0-9_-]+)*)\.([a-z0-9-]+):(\d{1,12})", str(item_id or ""))
    if not m:
        raise CmsError("CMS_NOT_FOUND", f"{item_id!r} is not a content id (expected e.g. home.hero.hero-slides:7).",
                       field="id")
    section_id, resource, pk = m.group(1), m.group(2), int(m.group(3))
    page, section = _section(section_id)
    if section["resource"] != resource:
        raise CmsError("CMS_NOT_FOUND", f"{item_id} does not exist.", field="id")
    model = _resource_models()[resource]
    qs = model.objects.filter(**section.get("filter", {}))
    obj = qs.filter(pk=pk).first()
    if obj is None:
        raise CmsError("CMS_NOT_FOUND", f"{item_id} does not exist (it may have been removed in the CMS).", field="id")
    return page, section, model, obj


# --------------------------------------------------------------------------- values
def _raw(obj) -> dict:
    """Storable DB values (for versions, before/after and discard)."""
    out = {}
    for f in obj._meta.concrete_fields:
        v = getattr(obj, f.attname)
        if isinstance(v, (dt.date, dt.datetime)):
            v = v.isoformat()
        elif hasattr(v, "name") and isinstance(f, models.FileField):
            v = v.name or ""
        out[f.attname] = v
    return out


def version_of(obj) -> int:
    # TODO(integration, backend-core): return obj.version (every row has `version`).
    blob = json.dumps(_raw(obj), sort_keys=True, default=str).encode()
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _media_url(name: str) -> str | None:
    return f"{settings.MEDIA_URL.rstrip('/')}/{name}" if name else None


def _values(obj, fields: list[dict]) -> dict:
    out = {}
    for spec in fields:
        name = spec["name"]
        if spec["type"] == "gallery":
            gallery = fallback.GALLERIES[_resource_of(obj)]
            child = getattr(obj, _related_name(obj, gallery))
            out[name] = [{"image": _media_url(c.image.name), "caption": getattr(c, "caption", "")} for c in child.all()]
            continue
        v = getattr(obj, name)
        if spec["type"] == "image":
            v = _media_url(v.name) if v else None
        elif isinstance(v, models.Model):
            v = str(v)
        elif isinstance(v, dt.date):
            v = v.isoformat()
        out[name] = v
    return out


def _resource_of(obj) -> str:
    for resource, model in _resource_models().items():
        if type(obj) is model:
            return resource
    raise KeyError(type(obj))


def _related_name(obj, gallery) -> str:
    child_model = _resource_models()[gallery["child"]]
    return child_model._meta.get_field(gallery["fk"]).remote_field.related_name


def _label(obj) -> str:
    return str(obj)[:120]


def _visible(obj) -> bool:
    return bool(getattr(obj, "is_published", True))


def preview_url(page_id: str, item_id: str | None = None) -> str:
    # TODO(integration, backend-core): apps.publishing.registry.preview_url(item_id) (same format).
    # Opens the page editor behind Cloudflare Access + CMS sign-in, never a bearer link.
    url = f"{settings.CMS_PUBLIC_URL}/pages/{quote(page_id)}"
    return f"{url}?{urlencode({'item': item_id})}" if item_id else url


# --------------------------------------------------------------------------- input coercion
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _richtext_to_html(value) -> str:
    """Structured rich text -> sanitised HTML. Allowed: paragraphs, H3, bulleted and numbered
    lists, bold, italic, links. Input shape: [{"type": "paragraph"|"heading"|"bulleted_list"|
    "numbered_list", "text": [spans] | "items": [[spans], ...]}], span = {"text", "bold"?,
    "italic"?, "link"?}. Plain strings are accepted as spans."""

    def spans(items) -> str:
        if isinstance(items, str):
            items = [{"text": items}]
        if not isinstance(items, list):
            raise CmsError("CMS_VALIDATION", "Rich text spans must be a list.", field="body")
        out = []
        for span in items:
            if isinstance(span, str):
                span = {"text": span}
            if not isinstance(span, dict) or not isinstance(span.get("text"), str):
                raise CmsError("CMS_VALIDATION", "Each rich text span needs a text string.", field="body")
            text = html.escape(_CONTROL.sub("", span["text"]))
            if span.get("bold"):
                text = f"<strong>{text}</strong>"
            if span.get("italic"):
                text = f"<em>{text}</em>"
            if span.get("link"):
                link = str(span["link"])
                if not (link.startswith("/") and not link.startswith("//")):
                    try:
                        URLValidator(schemes=["http", "https", "mailto"])(link)
                    except ValidationError:
                        raise CmsError("CMS_VALIDATION", f"{link!r} is not a valid link.", field="body") from None
                text = f'<a href="{html.escape(link, quote=True)}">{text}</a>'
            out.append(text)
        return "".join(out)

    if not isinstance(value, list):
        raise CmsError("CMS_VALIDATION", "Rich text must be a list of blocks (paragraph, heading, lists); HTML is "
                       "not accepted.", field="body")
    parts = []
    for block in value:
        kind = block.get("type") if isinstance(block, dict) else None
        if kind == "paragraph":
            parts.append(f"<p>{spans(block.get('text', []))}</p>")
        elif kind == "heading":
            parts.append(f"<h3>{spans(block.get('text', []))}</h3>")
        elif kind in ("bulleted_list", "numbered_list"):
            tag = "ul" if kind == "bulleted_list" else "ol"
            items = "".join(f"<li>{spans(i)}</li>" for i in block.get("items", []))
            parts.append(f"<{tag}>{items}</{tag}>")
        else:
            raise CmsError("CMS_VALIDATION", "Rich text blocks must be paragraph, heading, bulleted_list or "
                           "numbered_list.", field="body")
    return "".join(parts)


def _staged(actor: Actor, media_id, field: str) -> StagedImage:
    m = re.fullmatch(r"media:(\d{1,12})", str(media_id or ""))
    img = StagedImage.objects.filter(pk=int(m.group(1)), owner=actor.user).first() if m else None
    if img is None:
        raise CmsError("CMS_NOT_FOUND", f"{media_id!r} is not one of your uploaded photos.",
                       fix="Use a media id returned by upload_image_from_url, request_upload_link or search_media.",
                       field=field)
    return img


def _check_width(img: StagedImage, spec: dict, warnings: list[str]):
    minimum = spec.get("min_width")
    if minimum and img.width < minimum:
        raise CmsError("CMS_IMAGE_TOO_SMALL",
                       f"{spec['label']} photos must be at least {minimum} px wide; this one is "
                       f"{img.width} × {img.height}. Nothing was changed.", field=spec["name"])
    if img.width < 1200:
        warnings.append(f"The photo for {spec['name']} is only {img.width} px wide and may look soft on large screens.")


def _coerce(actor: Actor, spec: dict, value, warnings: list[str]):
    name, ftype = spec["name"], spec["type"]

    def bad(msg):
        return CmsError("CMS_VALIDATION", f"{name}: {msg}", field=name)

    if value is None:
        if spec.get("required"):
            raise bad("is required.")
        return "" if ftype in ("text", "textarea", "url", "richtext") else None
    if ftype in ("text", "textarea"):
        if not isinstance(value, str):
            raise bad("must be text.")
        value = _CONTROL.sub("", value).strip()
        if ftype == "text":
            value = " ".join(value.split())
        if spec.get("max") and len(value) > spec["max"]:
            raise bad(f"is {len(value)} characters; the limit is {spec['max']}.")
        if spec.get("required") and not value:
            raise bad("can't be empty.")
        return value
    if ftype == "richtext":
        return _richtext_to_html(value)
    if ftype == "url":
        value = str(value).strip()
        if value and not (value.startswith("/") and not value.startswith("//")):
            try:
                URLValidator(schemes=["http", "https", "mailto"])(value)
            except ValidationError:
                raise bad("must be a full https:// link or a site path such as /about.") from None
        if spec.get("max") and len(value) > spec["max"]:
            raise bad(f"is longer than {spec['max']} characters.")
        return value
    if ftype == "date":
        try:
            return dt.date.fromisoformat(str(value))
        except ValueError:
            raise bad("must be a date like 2026-12-12.") from None
    if ftype == "number":
        if isinstance(value, bool) or not isinstance(value, int):
            raise bad("must be a whole number.")
        return value
    if ftype == "boolean":
        if not isinstance(value, bool):
            raise bad("must be true or false.")
        return value
    if ftype == "select":
        choices = spec.get("choices", [])
        if str(value) not in choices:
            raise bad(f"must be one of: {', '.join(choices)}.")
        return str(value)
    if ftype == "image":
        img = _staged(actor, value, name)
        _check_width(img, spec, warnings)
        return img
    raise bad("can't be changed through Claude.")


def _apply(actor: Actor, obj, section: dict, fields: dict, *, creating: bool) -> tuple[list[str], list]:
    """Validate `fields` against the section schema and set them on obj. Returns
    (warnings, pending gallery photos)."""
    if not isinstance(fields, dict) or (not fields and not creating):
        raise CmsError("CMS_VALIDATION", "Send at least one field to change.", field="fields")
    schema = {f["name"]: f for f in section["fields"]}
    unknown = sorted(set(fields) - set(schema))
    if unknown:
        raise CmsError("CMS_VALIDATION", f"Unknown field(s) {', '.join(unknown)} for {section['label']}. "
                       f"Fields: {', '.join(schema)}.", field=unknown[0])
    warnings: list[str] = []
    photos = []
    names = list(schema) if creating else list(fields)
    for name in names:
        spec = schema[name]
        if spec["type"] == "gallery":
            if name in fields:
                photos = _coerce_gallery(actor, fields[name], warnings)
            continue
        if name not in fields:
            if creating and spec.get("required"):
                raise CmsError("CMS_VALIDATION", f"{name}: is required.", field=name)
            continue
        model_field = obj._meta.get_field(name)
        if isinstance(model_field, models.ForeignKey):
            options = {str(o): o for o in model_field.related_model.objects.all()}
            choice = options.get(str(fields[name]).strip()) if fields[name] is not None else None
            if choice is None:
                raise CmsError("CMS_VALIDATION", f"{name}: must be one of: {', '.join(options)}.", field=name)
            setattr(obj, name, choice)
            continue
        value = _coerce(actor, spec, fields[name], warnings)
        if spec["type"] == "image":
            if value is None:
                setattr(obj, name, None)
            else:
                f = getattr(obj, name)
                f.save(value.file.name.rsplit("/", 1)[-1], ContentFile(value.file.read()), save=False)
                value.file.close()
        elif value is None and model_field.null is False and spec["type"] in ("date", "number"):
            raise CmsError("CMS_VALIDATION", f"{name}: is required.", field=name)
        else:
            setattr(obj, name, value)
    return warnings, photos


def _coerce_gallery(actor: Actor, value, warnings) -> list:
    if not isinstance(value, list) or len(value) > 30:
        raise CmsError("CMS_VALIDATION", "photos must be a list (at most 30) of {media_id, caption}.", field="photos")
    out = []
    for entry in value:
        if isinstance(entry, str):
            entry = {"media_id": entry}
        if not isinstance(entry, dict):
            raise CmsError("CMS_VALIDATION", "Each photo needs a media_id.", field="photos")
        img = _staged(actor, entry.get("media_id"), "photos")
        caption = _CONTROL.sub("", str(entry.get("caption") or "")).strip()[:255]
        out.append((img, caption))
    return out


def _save_gallery(obj, photos):
    gallery = fallback.GALLERIES[_resource_of(obj)]
    child_model = _resource_models()[gallery["child"]]
    start = child_model.objects.filter(**{gallery["fk"]: obj}).count()
    for i, (img, caption) in enumerate(photos):
        child = child_model(**{gallery["fk"]: obj, "order": start + i})
        if hasattr(child, "caption"):
            child.caption = caption
        child.image.save(img.file.name.rsplit("/", 1)[-1], ContentFile(img.file.read()), save=False)
        img.file.close()
        child.save()


def _full_clean(obj):
    try:
        obj.full_clean(validate_unique=True)
    except ValidationError as exc:
        field, messages = next(iter(getattr(exc, "message_dict", {"fields": exc.messages}).items()))
        raise CmsError("CMS_VALIDATION", f"{field}: {' '.join(messages)}", field=field) from None


def _result(page: dict, section: dict, obj, *, kind: str, before, warnings=None, deduplicated=False) -> dict:
    item_id = make_item_id(section["id"], section["resource"], obj.pk)
    return {
        "id": item_id,
        "version": version_of(obj),
        "page": page["id"],
        "label": _label(obj),
        "preview_url": preview_url(page["id"], item_id),
        "status": "draft",
        "kind": kind,
        "before": before,
        "after": _raw(obj),
        "warnings": warnings or [],
        "deduplicated": deduplicated,
    }


# --------------------------------------------------------------------------- reads
def find_content(actor: Actor, query: str, limit: int = 10) -> list[dict]:
    tokens = [t for t in re.split(r"[\s.,;:'\"()]+", (query or "").casefold()) if t]
    if not tokens:
        raise CmsError("CMS_VALIDATION", "Give a name or a few words to search for.", field="query")
    resources = _resource_models()
    hits = []
    for page in registry_pages():
        for section in page["sections"]:
            text_fields = [f["name"] for f in section["fields"] if f["type"] in ("text", "textarea", "richtext", "date")]
            model = resources[section["resource"]]
            qs = model.objects.filter(**section.get("filter", {}))
            if section["kind"] == "singleton":
                qs = qs[:1]
            for obj in qs:
                values = {n: str(getattr(obj, n) or "") for n in text_fields}
                label = _label(obj)
                hay = (label + " " + " ".join(values.values())).casefold()
                if all(t in hay for t in tokens):
                    matched = next((n for n, v in values.items() if tokens[0] in v.casefold()), None)
                    snippet = re.sub(r"<[^>]+>", "", values.get(matched, "") if matched else label)[:160]
                    score = 2 if all(t in label.casefold() for t in tokens) else 1
                    item_id = make_item_id(section["id"], section["resource"], obj.pk)
                    hits.append((score, {
                        "id": item_id, "label": label, "page": page["id"], "section": section["id"],
                        "section_label": section["label"], "matched_field": matched, "snippet": snippet,
                        "visible": _visible(obj), "version": version_of(obj),
                    }))
    hits.sort(key=lambda h: -h[0])
    return [h for _, h in hits[:limit]]


def get_page(actor: Actor, page_id: str) -> dict:
    page = _page(page_id)
    model_for = _resource_models()
    sections = []
    for section in page["sections"]:
        model = model_for[section["resource"]]
        qs = model.objects.filter(**section.get("filter", {}))
        fields = section["fields"]
        out = {k: section[k] for k in ("id", "label", "kind", "resource")}
        out["fields"] = fields
        if section["kind"] == "singleton":
            obj = model.load() if hasattr(model, "load") else qs.first()
            out["item"] = {"id": make_item_id(section["id"], section["resource"], obj.pk),
                           "version": version_of(obj), "values": _values(obj, fields)}
        else:
            ordering = ["order", "id"] if any(f.name == "order" for f in model._meta.fields) else ["id"]
            out["items"] = [
                {"id": make_item_id(section["id"], section["resource"], obj.pk), "position": i + 1,
                 "label": _label(obj), "visible": _visible(obj), "version": version_of(obj),
                 "values": _values(obj, fields)}
                for i, obj in enumerate(qs.order_by(*ordering))
            ]
        sections.append(out)
    return {"page": page["id"], "title": page["title"], "path": page["path"],
            "preview_url": preview_url(page["id"]), "sections": sections}


def list_pending_changes(actor: Actor) -> dict:
    # TODO(integration, backend-core): apps.publishing.changes.pending_changes(session_id=...)
    # (same shape as GET /cms/changes/, every channel). This fallback lists Claude's own changes.
    writes = (ConnectorWrite.objects.filter(session__user=actor.user, discarded=False)
              .select_related("session").order_by("id"))
    pages: dict[str, list] = {}
    for w in writes:
        page_id = w.item_id.split(".", 1)[0]
        pages.setdefault(page_id, []).append({
            "id": w.item_id, "kind": w.kind, "channel": "mcp",
            "this_conversation": w.session.key == actor.session_key, "at": w.created_at.isoformat(),
        })
    count = sum(len(v) for v in pages.values())
    return {"count": count, "pages": [{"page": p, "preview_url": preview_url(p), "changes": c}
                                      for p, c in pages.items()]}


def search_media(actor: Actor, query: str, limit: int = 20) -> list[dict]:
    # TODO(integration, backend-core): search apps.publishing.models.MediaAsset (media ids stay
    # "media:<MediaAsset id>").
    q = (query or "").strip()
    qs = StagedImage.objects.filter(owner=actor.user).order_by("-id")
    if q:
        qs = qs.filter(models.Q(source__icontains=q) | models.Q(file__icontains=q))
    return [{"media_id": f"media:{m.pk}", "url": _media_url(m.file.name), "width": m.width, "height": m.height,
             "source": m.source, "uploaded_at": m.created_at.isoformat()} for m in qs[:limit]]


def get_preview_link(actor: Actor, page_id: str, item_id: str | None = None) -> dict:
    page = _page(page_id)
    if item_id:
        _parse_item_id(item_id)
    return {"page": page["id"], "preview_url": preview_url(page["id"], item_id),
            "note": "Opens the CMS page editor with unpublished changes applied. The person must be signed in to the CMS."}


# --------------------------------------------------------------------------- writes
def _stale(item_id: str, sent, current: int) -> CmsError:
    return CmsError("CMS_STALE_VERSION",
                    f"{item_id} changed since you read it (you sent v{sent}, current v{current}). No changes were saved.",
                    fix="Call get_page for this page and reapply your change to the current values.",
                    current_version=current, field="expected_version")


@transaction.atomic
def update_item(actor: Actor, item_id: str, fields: dict, expected_version: int) -> dict:
    # TODO(integration, backend-core): apps.publishing.content.update_by_item_id(item_id, data,
    # ctx=ctx, expected_version=...) (writes the audit entry itself); image fields via
    # content.attach_media(resource, pk, field, media_id, ctx=, expected_version=).
    page, section, model, obj = _parse_item_id(item_id)
    obj = model.objects.select_for_update().get(pk=obj.pk)
    current = version_of(obj)
    if expected_version != current:
        raise _stale(item_id, expected_version, current)
    before = _raw(obj)
    warnings, photos = _apply(actor, obj, section, fields, creating=False)
    _full_clean(obj)
    obj.save()
    if photos:
        _save_gallery(obj, photos)
    return _result(page, section, obj, kind="changed", before=before, warnings=warnings)


@transaction.atomic
def create_item(actor: Actor, section_id: str, fields: dict) -> dict:
    # TODO(integration, backend-core): apps.publishing.content.create_item(resource, data, ctx=ctx)
    # (apply the section's registry "defaults"). Dedupe stays in guardrails.py.
    page, section = _section(section_id)
    if section["kind"] != "collection":
        raise CmsError("CMS_VALIDATION", f"{section['label']} is a single block; use update_section to change it.",
                       field="section")
    model = _resource_models()[section["resource"]]
    obj = model(**section.get("filter", {}))
    warnings, photos = _apply(actor, obj, section, fields, creating=True)
    if any(f.name == "slug" for f in model._meta.fields) and not obj.slug:
        base = slugify(getattr(obj, "title", "") or "item")[:200] or "item"
        slug, n = base, 2
        while model.objects.filter(slug=slug).exists():
            slug, n = f"{base}-{n}", n + 1
        obj.slug = slug
    if any(f.name == "order" for f in model._meta.fields):
        last = model.objects.filter(**section.get("filter", {})).aggregate(m=models.Max("order"))["m"]
        obj.order = (last + 1) if last is not None else 0
    _full_clean(obj)
    obj.save()
    if photos:
        _save_gallery(obj, photos)
    return _result(page, section, obj, kind="added", before=None, warnings=warnings)


@transaction.atomic
def hide_item(actor: Actor, item_id: str, expected_version: int) -> dict:
    page, section, model, obj = _parse_item_id(item_id)
    if not any(f.name == "is_published" for f in model._meta.fields):
        raise CmsError("CMS_VALIDATION", f"{section['label']} items can't be hidden; they can only be removed in the "
                       "CMS by a Publisher.", field="id")
    obj = model.objects.select_for_update().get(pk=obj.pk)
    current = version_of(obj)
    if expected_version != current:
        raise _stale(item_id, expected_version, current)
    before = _raw(obj)
    obj.is_published = False
    obj.save(update_fields=["is_published"])
    return _result(page, section, obj, kind="hidden", before=before)


@transaction.atomic
def reorder(actor: Actor, section_id: str, item_ids: list[str]) -> dict:
    # TODO(integration, backend-core): apps.publishing.content.reorder(resource, ids, ctx=ctx).
    page, section = _section(section_id)
    model = _resource_models()[section["resource"]]
    if section["kind"] != "collection" or not any(f.name == "order" for f in model._meta.fields):
        raise CmsError("CMS_VALIDATION", f"{section['label']} can't be reordered.", field="section")
    if not isinstance(item_ids, list) or not item_ids:
        raise CmsError("CMS_VALIDATION", "Send the full list of item ids in the new order.", field="ids")
    pks = []
    for item_id in item_ids:
        _, s, _, obj = _parse_item_id(item_id)
        if s["id"] != section["id"]:
            raise CmsError("CMS_VALIDATION", f"{item_id} is not in {section_id}.", field="ids")
        pks.append(obj.pk)
    qs = model.objects.select_for_update().filter(**section.get("filter", {}))
    existing = {o.pk: o.order for o in qs}
    if sorted(pks) != sorted(existing):
        missing = [make_item_id(section_id, section["resource"], pk) for pk in existing if pk not in pks]
        raise CmsError("CMS_VALIDATION", "The list must contain every item of the section exactly once. "
                       f"Missing: {', '.join(missing) or 'none'}.", field="ids")
    before = {str(pk): existing[pk] for pk in existing}
    model.objects.bulk_update([model(pk=pk, order=i) for i, pk in enumerate(pks)], ["order"])
    return {"id": section_id, "version": None, "page": page["id"], "label": section["label"],
            "preview_url": preview_url(page["id"]), "status": "draft", "kind": "reordered",
            "before": before, "after": {str(pk): i for i, pk in enumerate(pks)}, "warnings": [],
            "deduplicated": False}


def _restore(model, pk, raw: dict | None, kind: str):
    if kind == "reordered":
        model.objects.bulk_update([model(pk=int(k), order=v) for k, v in raw.items()
                                   if model.objects.filter(pk=int(k)).exists()], ["order"])
        return
    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        return
    if kind == "added":
        # Fallback can't tell whether a Publisher has published the row since, so it never
        # deletes: it hides the row. Core's discard removes never-published rows properly.
        if not hasattr(obj, "is_published"):
            raise CmsError("CMS_VALIDATION", "This new item can't be undone from Claude yet; remove it in the CMS.",
                           fix="Tell the user to remove it in the CMS editor.", field="id")
        obj.is_published = False
        obj.save(update_fields=["is_published"])
        return
    for f in obj._meta.concrete_fields:
        if f.attname in raw and not f.primary_key:
            setattr(obj, f.attname, f.to_python(raw[f.attname]) if raw[f.attname] is not None else None)
    obj.save()


@transaction.atomic
def discard_change(actor: Actor, item_id: str) -> dict:
    # TODO(integration, backend-core): apps.publishing.changes.discard_item(item_id, ctx=ctx) —
    # reverts to the last PUBLISHED values whoever changed it. Fallback: undo this user's
    # Claude changes on it.
    writes = list(ConnectorWrite.objects.select_for_update()
                  .filter(session__user=actor.user, item_id=item_id, discarded=False).order_by("id"))
    if not writes:
        raise CmsError("CMS_NOT_FOUND", f"There is no unpublished change from Claude on {item_id}.",
                       fix="Changes made in the CMS editor can be discarded there.", field="id")
    _undo(writes)
    return {"id": item_id, "discarded": len(writes), "status": "draft"}


@transaction.atomic
def discard_session(actor: Actor) -> dict:
    # TODO(integration, backend-core): apps.publishing.changes.discard_session(actor.session_key, ctx=ctx).
    writes = list(ConnectorWrite.objects.select_for_update()
                  .filter(session__key=actor.session_key, session__user=actor.user, discarded=False).order_by("id"))
    by_item: dict[str, list] = {}
    for w in writes:
        by_item.setdefault(w.item_id, []).append(w)
    for item_writes in reversed(list(by_item.values())):
        _undo(item_writes)
    return {"discarded": len(writes), "items": list(by_item), "status": "draft"}


def _undo(writes: list[ConnectorWrite]):
    first = writes[0]
    resources = _resource_models()
    if first.kind == "reordered":
        _, section = _section(first.item_id)
        model = resources[section["resource"]]
        _restore(model, None, first.before, "reordered")
    else:
        resource, pk = first.item_id.rsplit(".", 1)[1].split(":")
        _restore(resources[resource], int(pk), first.before, first.kind)
    ConnectorWrite.objects.filter(pk__in=[w.pk for w in writes]).update(discarded=True)


def request_upload_link(actor: Actor) -> dict:
    # TODO(integration, backend-core): apps.publishing.uploads.create_upload_link(user, ctx=ctx)
    # → {url, token, expires_at}; uploads.link_status(token) gives the MediaAsset id afterwards.
    try:
        from apps.publishing.uploads import create_upload_link  # type: ignore
    except ImportError:
        raise CmsError("CMS_INTERNAL", "Photo upload links aren't available on this server yet.",
                       fix="Ask the user for a public https link to the photo and use upload_image_from_url, or "
                           "ask them to upload it in the CMS.", retryable=False) from None
    from apps.publishing.audit import WriteContext  # type: ignore  # pragma: no cover

    ctx = WriteContext(user=actor.user, channel="mcp", connector_session=actor.session_key)  # pragma: no cover
    link = create_upload_link(actor.user, ctx=ctx)  # pragma: no cover
    return {"upload_url": link["url"], "expires_at": link["expires_at"]}  # pragma: no cover


def fetch_image_from_url(actor: Actor, url: str, *, resolver=None, connector=None) -> dict:
    data, source = fetch_image_bytes(url, resolver=resolver, connector=connector)
    processed = process_image(data)
    existing = StagedImage.objects.filter(owner=actor.user, sha256=processed.sha256).first()
    if existing:
        img, deduplicated = existing, True
    else:
        img = StagedImage(owner=actor.user, sha256=processed.sha256, width=processed.width,
                          height=processed.height, source=source)
        img.file.save(f"{processed.sha256[:16]}.{processed.ext}", ContentFile(processed.content), save=False)
        img.save()
        deduplicated = False
    return {"media_id": f"media:{img.pk}", "width": img.width, "height": img.height,
            "url": _media_url(img.file.name), "deduplicated": deduplicated}


def request_review(actor: Actor, note: str) -> dict:
    # TODO(integration, backend-core): apps.publishing.review.request_review(user, note, ctx=ctx).
    note = _CONTROL.sub("", str(note or "")).strip()[:1000]
    User = get_user_model()
    publishers = User.objects.filter(is_active=True).filter(
        models.Q(groups__name__in=["publisher", "admin"]) | models.Q(is_superuser=True)
    ).exclude(email="").distinct()
    emails = sorted({u.email for u in publishers})
    name = actor.user.get_full_name() or actor.user.get_username()
    if emails:
        send_mail(
            subject=f"CRTDH website: {name} asked for a review",
            message=(f"{name} made website changes with Claude and asked a Publisher to review them.\n\n"
                     f"Note: {note or '(none)'}\n\nReview and publish: {settings.CMS_PUBLIC_URL}/review\n"),
            from_email=None, recipient_list=emails, fail_silently=False,
        )
    return {"notified": len(emails), "status": "waiting_for_review"}


def describe_item(actor: Actor, item_id: str) -> dict:
    page, section, _, obj = _parse_item_id(item_id)
    return {"id": item_id, "version": version_of(obj), "page": page["id"], "label": _label(obj),
            "preview_url": preview_url(page["id"], item_id), "status": "draft", "kind": None, "warnings": []}
