"""The only module in mcp_server that touches CMS internals.

Every other MCP module calls these functions. Content is read through the section registry
(`apps.publishing.registry`) and written only through `apps.publishing` (content, changes,
review, uploads), which validates with the resources' serializers, checks `expected_version`,
and writes the audit log with channel "mcp" and the connector session
(`WriteContext(user, channel="mcp", connector_session=<Mcp-Session-Id>)`). QA's import-linter
contract forbids importing content apps' models/serializers here.

Item ids follow contracts §2: `<section id>.<resource>:<pk>`, e.g. `home.hero.hero-slides:7`;
child rows (event photos, innovation photos, photo-grid photos, product photos) use their
parent's section id, e.g. `media.events.media-event-images:12`.

MCP-specific behaviour kept on top of core: field schemas for tools, rich-text blocks instead
of HTML, photo ownership (a media id must be one of the caller's uploads), required fields on
create, the "photos" gallery shortcut, and discard that never overwrites someone else's edit.

All functions are synchronous (Django ORM); the tool layer runs them in a worker thread.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import html
import re
from dataclasses import dataclass
from functools import cache
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.errors import DEFAULT_FIX as CORE_DEFAULT_FIX
from apps.common.errors import CMSError
from apps.common.errors import as_error_body
from apps.publishing import audit, changes, content, registry, review, uploads
from apps.publishing.audit import WriteContext
from apps.publishing.models import AuditEntry, MediaAsset

from .errors import CODES, CmsError
from .fetch import fetch_image_bytes
from .images import process_image
from .models import ConnectorWrite


@dataclass(frozen=True)
class Actor:
    """Who is calling: the CMS user behind the OAuth token and the MCP connector session."""

    user: Any
    session_key: str
    request_id: str

    @property
    def ctx(self) -> WriteContext:
        return WriteContext(user=self.user, channel="mcp", connector_session=self.session_key[:64])


# --------------------------------------------------------------------------- core errors
_PASS_THROUGH_EXTRA = ("edited_by", "edited_at")


def from_core(exc) -> CmsError:
    """apps.publishing / apps.common CMSError or DRF ValidationError -> the MCP error (same §4 body).
    Core's generic fix texts are replaced by tool-aware ones; specific ones are kept."""
    body = exc.body if isinstance(exc, CMSError) else as_error_body(exc)
    code = body.get("code") if body.get("code") in CODES else "CMS_INTERNAL"
    fix = body.get("fix")
    if code != body.get("code") or fix == CORE_DEFAULT_FIX.get(body.get("code")):
        fix = None
    return CmsError(code, body.get("message") or "The CMS refused this change.", fix=fix, field=body.get("field"),
                    current_version=body.get("current_version"),
                    extra={k: body[k] for k in _PASS_THROUGH_EXTRA if body.get(k) is not None})


@contextlib.contextmanager
def _core():
    try:
        yield
    except (CMSError, DRFValidationError) as exc:
        raise from_core(exc) from None


# --------------------------------------------------------------------------- registry
SITE_PAGE = {"id": "site", "path": None, "title": "Header and footer (every page)"}


def page_ids() -> list[str]:
    return [p["id"] for p in registry.REGISTRY["pages"]] + [SITE_PAGE["id"]]


def has_visibility(resource: str) -> bool:
    return registry.RESOURCES[resource].has_visibility


def _model(resource: str):
    return registry.RESOURCES[resource].model_class


@cache
def _exported() -> dict[tuple[str, str], dict]:
    """(section id, resource) -> exported section/child view (fields enriched from the models)."""
    out = {}
    exported = registry.export_registry()
    for s in [x for p in exported["pages"] for x in p["sections"]] + exported["globals"]:
        out[(s["id"], s["resource"])] = s
        for child in s.get("children") or []:
            out[(s["id"], child["resource"])] = child
    return out


def _max_length(resource: str, name: str) -> int | None:
    try:
        return getattr(_model(resource)._meta.get_field(name), "max_length", None)
    except Exception:  # noqa: BLE001 - registry-only name
        return None


def _gallery_child(view: dict) -> dict | None:
    """The child list that holds a section item's photos (first child list with an image field)."""
    for child in view.get("children") or []:
        if any(fd["type"] == "image" for fd in child["fields"]):
            return child
    return None


def _field_specs(view: dict) -> list[dict]:
    """Fields Claude may write in a section (or child list) view, in the MCP tool shape.

    Not offered: file uploads (PDF/video: done in the CMS), visibility (hide_* tools), order
    (reorder), focus points, and keys that place a row (a page filter or the parent of a child
    row) — changing those would move the row somewhere else."""
    exported = _exported()[(view["id"], view["resource"])]
    fixed = {k for k in (view.get("filter") or {}) if "__" not in k}
    if view.get("parent_field"):
        fixed.add(view["parent_field"])
    specs = []
    for fd in exported["fields"]:
        if fd["type"] == "file" or fd["name"] in fixed:
            continue
        spec: dict[str, Any] = {"name": fd["name"], "type": fd["type"],
                                "label": fd.get("label") or fd["name"].replace("_", " ").capitalize()}
        for key in ("max", "min_width", "help"):
            if fd.get(key):
                spec[key] = fd[key]
        if fd.get("required"):
            spec["required"] = True
        if fd.get("choices_resource"):
            spec["choices_resource"] = fd["choices_resource"]
            spec["choice_label"] = fd.get("choice_label", "name")
            noun = _model(fd["choices_resource"])._meta.verbose_name
            spec["help"] = f"Name of an existing {noun}."
        elif fd.get("choices"):
            spec["choices"] = [str(c["value"]) if isinstance(c, dict) else str(c) for c in fd["choices"]]
            labels = {str(c["value"]): str(c["label"]) for c in fd["choices"] if isinstance(c, dict)}
            if labels:
                spec["choice_labels"] = labels
        specs.append(spec)
        if fd["type"] == "image" and fd.get("alt_field"):
            alt = {"name": fd["alt_field"], "type": "text", "label": f"{spec['label']}: description for screen readers"}
            if _max_length(view["resource"], fd["alt_field"]):
                alt["max"] = _max_length(view["resource"], fd["alt_field"])
            specs.append(alt)
    gallery = _gallery_child(view) if view["kind"] == "collection" and not view.get("parent_field") else None
    if gallery is not None:
        specs.append({"name": "photos", "type": "gallery", "label": gallery.get("label") or "Photos",
                      "help": "List of {media_id, caption}. Adds photos to this item."})
    return specs


def _public_view(page_id: str, view: dict) -> dict:
    out = {k: view[k] for k in ("id", "label", "kind", "resource") if k in view}
    if view.get("description"):
        out["description"] = view["description"]
    if view.get("filter"):
        out["filter"] = view["filter"]
    out["fields"] = _field_specs(view)
    return out


def registry_pages() -> list[dict]:
    """Pages with sections and field schemas (contracts §2 shape), plus the site-wide sections as page "site"."""
    pages = [{"id": p["id"], "path": p["path"], "title": p["title"],
              "sections": [_public_view(p["id"], s) for s in p["sections"]]} for p in registry.REGISTRY["pages"]]
    pages.append({**SITE_PAGE, "sections": [_public_view("site", s) for s in registry.REGISTRY["globals"]]})
    return pages


def _page(page_id: str) -> dict:
    for page in registry_pages():
        if page["id"] == page_id:
            return page
    raise CmsError("CMS_NOT_FOUND", f"There is no page called {page_id!r}. Pages: {', '.join(page_ids())}.",
                   fix="Use one of the listed page ids.", field="page")


def _section(section_id: str) -> tuple[dict, dict]:
    """-> (page {id,title}, raw registry section view). Top-level sections only."""
    hit = registry.section_index().get(str(section_id or ""))
    if hit is None:
        raise CmsError("CMS_NOT_FOUND", f"There is no section {section_id!r}.", field="section")
    page_id, section = hit
    return {"id": page_id}, section


def section_fields(section_id: str) -> list[dict]:
    _, section = _section(section_id)
    return _field_specs(section)


def make_item_id(section_id: str, resource: str, pk: int) -> str:
    return f"{section_id}.{resource}:{pk}"


def _queryset(view: dict):
    qs = _model(view["resource"]).objects.all()
    return qs.filter(**view["filter"]) if view.get("filter") else qs


def _parse_item_id(item_id: str):
    """-> (page_id, view, resource, obj). Raises CMS_NOT_FOUND."""
    try:
        page_id, view, resource, pk = registry.view_for_item(str(item_id or ""))
    except (ValueError, KeyError):
        raise CmsError("CMS_NOT_FOUND", f"{item_id!r} is not a content id (expected e.g. home.hero.hero-slides:7).",
                       field="id") from None
    if view["kind"] == "singleton":
        obj = _model(resource).load()
        if obj.pk != pk:
            obj = None
    else:
        obj = _queryset(view).filter(pk=pk).first()
    if obj is None:
        raise CmsError("CMS_NOT_FOUND", f"{item_id} does not exist (it may have been removed in the CMS).", field="id")
    return page_id, view, resource, obj


# --------------------------------------------------------------------------- values
def version_of(obj) -> int:
    return obj.version


def _media_url(name: str) -> str | None:
    return f"{settings.MEDIA_URL.rstrip('/')}/{name}" if name else None


def _values(obj, fields: list[dict]) -> dict:
    out = {}
    for spec in fields:
        name = spec["name"]
        if spec["type"] == "gallery":
            continue  # photos are listed as the item's children
        v = getattr(obj, name, None)
        if spec["type"] == "image":
            v = _media_url(v.name) if v else None
        elif spec.get("choices_resource"):
            v = getattr(v, spec["choice_label"], str(v)) if v is not None else None
        elif isinstance(v, (dt.date, dt.datetime)):
            v = v.isoformat()
        out[name] = v
    return out


def _label(obj) -> str:
    return str(obj)[:120]


def _visible(obj) -> bool:
    return bool(getattr(obj, "is_published", True))


def preview_url(page_id: str, item_id: str | None = None) -> str:
    # Opens the page editor behind Cloudflare Access + CMS sign-in, never a bearer link.
    if item_id:
        return registry.preview_url(item_id)
    return f"{settings.CMS_PUBLIC_URL.rstrip('/')}/pages/{page_id}"


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


def _media(actor: Actor, media_id, field: str) -> MediaAsset:
    """A photo the caller uploaded (upload link or upload_image_from_url). Others' uploads are not usable."""
    m = re.fullmatch(r"media:(\d{1,12})", str(media_id or ""))
    asset = MediaAsset.objects.filter(pk=int(m.group(1)), uploaded_by=actor.user).first() if m else None
    if asset is None:
        raise CmsError("CMS_NOT_FOUND", f"{media_id!r} is not one of your uploaded photos.",
                       fix="Use a media id returned by upload_image_from_url, request_upload_link or search_media.",
                       field=field)
    return asset


def _check_width(asset: MediaAsset, spec: dict, warnings: list[str]):
    minimum = spec.get("min_width")
    width = asset.width or 0
    if minimum and width < minimum:
        raise CmsError("CMS_IMAGE_TOO_SMALL",
                       f"{spec['label']} photos must be at least {minimum} px wide; this one is "
                       f"{width} × {asset.height} px. Nothing was changed.", field=spec["name"])
    if width < registry.WARN_WIDTH:
        warnings.append(f"The photo for {spec['name']} is only {width} px wide and may look soft on large screens.")


def _choice(spec: dict, value):
    """Select value -> stored value. Accepts the stored value or its label (case-insensitive)."""
    name = spec["name"]
    if spec.get("choices_resource"):
        model = _model(spec["choices_resource"])
        options = {str(getattr(o, spec["choice_label"], o)): o.pk for o in model.objects.all()}
        wanted = str(value).strip().casefold()
        pk = next((pk for label, pk in options.items() if label.casefold() == wanted), None)
        if pk is None and isinstance(value, int) and value in options.values():
            pk = value
        if pk is None:
            raise CmsError("CMS_VALIDATION", f"{name}: must be one of: {', '.join(options)}.", field=name)
        return pk
    choices = spec.get("choices", [])
    labels = spec.get("choice_labels", {})
    wanted = str(value).strip()
    for v in choices:
        if wanted == v or wanted.casefold() == labels.get(v, "\0").casefold():
            return v
    shown = [f"{v} ({labels[v]})" if v in labels else v for v in choices]
    raise CmsError("CMS_VALIDATION", f"{name}: must be one of: {', '.join(shown)}.", field=name)


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
            return dt.date.fromisoformat(str(value)).isoformat()
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
        return _choice(spec, value)
    if ftype == "image":
        asset = _media(actor, value, name)
        _check_width(asset, spec, warnings)
        return asset
    raise bad("can't be changed through Claude.")


def _prepare(actor: Actor, view: dict, fields: dict, *, creating: bool):
    """Validate `fields` against the view's MCP schema.
    Returns (data for the serializer, {image field: MediaAsset}, gallery photos, warnings)."""
    if not isinstance(fields, dict) or (not fields and not creating):
        raise CmsError("CMS_VALIDATION", "Send at least one field to change.", field="fields")
    schema = {f["name"]: f for f in _field_specs(view)}
    unknown = sorted(set(fields) - set(schema))
    if unknown:
        raise CmsError("CMS_VALIDATION", f"Unknown field(s) {', '.join(unknown)} for {view.get('label', view['id'])}. "
                       f"Fields: {', '.join(schema)}.", field=unknown[0])
    data, images, photos, warnings = {}, {}, [], []
    for name in (list(schema) if creating else list(fields)):
        spec = schema[name]
        if name not in fields:
            if creating and spec.get("required"):
                raise CmsError("CMS_VALIDATION", f"{name}: is required.", field=name)
            continue
        if spec["type"] == "gallery":
            photos = _coerce_gallery(actor, fields[name])
            continue
        value = _coerce(actor, spec, fields[name], warnings)
        if spec["type"] == "image":
            if value is None:
                raise CmsError("CMS_VALIDATION", f"{name}: photos can be replaced through Claude, not removed.",
                               fix="Hide the item instead, or remove the photo in the CMS.", field=name)
            images[name] = value
        else:
            data[name] = value
    return data, images, photos, warnings


def _coerce_gallery(actor: Actor, value) -> list:
    if not isinstance(value, list) or len(value) > 30:
        raise CmsError("CMS_VALIDATION", "photos must be a list (at most 30) of {media_id, caption}.", field="photos")
    out = []
    for entry in value:
        if isinstance(entry, str):
            entry = {"media_id": entry}
        if not isinstance(entry, dict):
            raise CmsError("CMS_VALIDATION", "Each photo needs a media_id.", field="photos")
        asset = _media(actor, entry.get("media_id"), "photos")
        caption = _CONTROL.sub("", str(entry.get("caption") or "")).strip()[:255]
        out.append((asset, caption))
    return out


def _attach_images(actor: Actor, resource: str, obj, images: dict):
    for name, asset in images.items():
        with _core():
            obj = content.attach_media(resource, obj.pk, name, asset.pk, ctx=actor.ctx, expected_version=obj.version)
    return obj


def _add_photos(actor: Actor, section: dict, parent, photos: list):
    """Child rows for the "photos" shortcut. A new (hidden) parent's photos are visible, so a Publisher
    shows the item with its photos in one step; photos added to an item already on the site start hidden
    (addendum A3) until a Publisher shows them."""
    child = _gallery_child(section)
    if not photos or child is None:
        return
    resource, parent_field = child["resource"], child["parent_field"]
    show = not _visible(parent)
    has_caption = any(fd["name"] == "caption" for fd in child["fields"])
    image_field = next(fd["name"] for fd in child["fields"] if fd["type"] == "image")
    for asset, caption in photos:
        data = {parent_field: parent.pk}
        if has_caption and caption:
            data["caption"] = caption
        with _core():
            row = content.create_item(resource, data, ctx=actor.ctx, section_id=section["id"])
            row = content.attach_media(resource, row.pk, image_field, asset.pk, ctx=actor.ctx,
                                       expected_version=row.version)
            if show and has_visibility(resource):
                content.update_item(resource, row.pk, {"is_published": True}, ctx=actor.ctx,
                                    expected_version=row.version)


def _result(page_id: str, item_id: str, obj, *, kind: str, before, warnings=None, deduplicated=False) -> dict:
    return {
        "id": item_id,
        "version": version_of(obj),
        "page": page_id,
        "label": _label(obj),
        "preview_url": preview_url(page_id, item_id),
        "status": "draft",
        "kind": kind,
        "before": before,
        "after": audit.row_values(obj),
        "warnings": warnings or [],
        "deduplicated": deduplicated,
    }


# --------------------------------------------------------------------------- reads
def find_content(actor: Actor, query: str, limit: int = 10) -> list[dict]:
    tokens = [t for t in re.split(r"[\s.,;:'\"()]+", (query or "").casefold()) if t]
    if not tokens:
        raise CmsError("CMS_VALIDATION", "Give a name or a few words to search for.", field="query")
    hits = []
    for page_id, view in registry.all_views():
        specs = _field_specs(view)
        text_fields = [f["name"] for f in specs if f["type"] in ("text", "textarea", "richtext", "date")]
        if not text_fields:
            continue
        objs = [_model(view["resource"]).load()] if view["kind"] == "singleton" else _queryset(view)
        for obj in objs:
            values = {n: str(getattr(obj, n, "") or "") for n in text_fields}
            label = _label(obj)
            hay = (label + " " + " ".join(values.values())).casefold()
            if all(t in hay for t in tokens):
                matched = next((n for n, v in values.items() if tokens[0] in v.casefold()), None)
                snippet = re.sub(r"<[^>]+>", "", values.get(matched, "") if matched else label)[:160]
                score = 2 if all(t in label.casefold() for t in tokens) else 1
                hits.append((score, {
                    "id": make_item_id(view["id"], view["resource"], obj.pk), "label": label, "page": page_id,
                    "section": view["id"], "section_label": view.get("label", ""), "matched_field": matched,
                    "snippet": snippet, "visible": _visible(obj), "version": version_of(obj),
                }))
    hits.sort(key=lambda h: -h[0])
    return [h for _, h in hits[:limit]]


def _ordered(qs):
    model = qs.model
    return qs.order_by(*(["order", "id"] if any(f.name == "order" for f in model._meta.fields) else ["id"]))


def _items(view: dict, qs, fields: list[dict]) -> list[dict]:
    children = [c for c in (view.get("children") or [])]
    out = []
    for i, obj in enumerate(_ordered(qs)):
        item = {"id": make_item_id(view["id"], view["resource"], obj.pk), "position": i + 1,
                "label": _label(obj), "visible": _visible(obj), "version": version_of(obj),
                "values": _values(obj, fields)}
        if children:
            item["children"] = []
            for child in children:
                cview = registry.section_view(view["id"], child["resource"])
                cfields = _field_specs(cview)
                cqs = _model(child["resource"]).objects.filter(**{child["parent_field"]: obj.pk})
                item["children"].append({"resource": child["resource"], "label": child.get("label", ""),
                                         "items": _items(cview, cqs, cfields)})
        out.append(item)
    return out


def get_page(actor: Actor, page_id: str) -> dict:
    page = _page(page_id)
    raw = {s["id"]: s for _p, s in registry.all_sections()}
    sections = []
    for section in page["sections"]:
        view = raw[section["id"]]
        out = dict(section)
        if view.get("children"):
            out["children"] = [{"resource": c["resource"], "label": c.get("label", ""),
                                "fields": _field_specs(registry.section_view(view["id"], c["resource"]))}
                               for c in view["children"]]
        if view["kind"] == "singleton":
            obj = _model(view["resource"]).load()
            out["item"] = {"id": make_item_id(view["id"], view["resource"], obj.pk),
                           "version": version_of(obj), "values": _values(obj, section["fields"])}
        else:
            out["items"] = _items(view, _queryset(view), section["fields"])
        sections.append(out)
    return {"page": page["id"], "title": page["title"], "path": page["path"],
            "preview_url": preview_url(page["id"]), "sections": sections}


def list_pending_changes(actor: Actor) -> dict:
    """Every unpublished change waiting for a Publisher (any editor or channel, as on the CMS review
    screen), marking the ones this conversation made."""
    with _core():
        data = changes.pending_changes()
    pages = []
    for page in data["pages"]:
        out = []
        for c in page["changes"]:
            out.append({
                "id": c["item_id"], "label": c["label"], "section": c.get("section"), "kind": c["kind"],
                "fields": [f["label"] for f in c.get("fields", [])], "author": c.get("author"),
                "channel": c.get("channel"), "at": c["at"].isoformat() if hasattr(c.get("at"), "isoformat") else c.get("at"),
                "this_conversation": bool(c.get("session_id")) and c.get("session_id") == actor.session_key[:64],
            })
        pages.append({"page": page["page"], "title": page["title"], "preview_url": preview_url(page["page"]),
                      "changes": out})
    review_request = data.get("review_request")
    if review_request and hasattr(review_request.get("at"), "isoformat"):
        review_request = {**review_request, "at": review_request["at"].isoformat()}
    return {"count": data["count"], "pages": pages, "review_request": review_request}


def search_media(actor: Actor, query: str, limit: int = 20) -> list[dict]:
    """The caller's own photos (upload links and upload_image_from_url), newest first."""
    q = (query or "").strip()
    qs = MediaAsset.objects.filter(uploaded_by=actor.user).order_by("-id")
    if q:
        qs = qs.filter(file__icontains=q)
    return [{"media_id": f"media:{m.pk}", "url": _media_url(m.file.name), "width": m.width, "height": m.height,
             "uploaded_at": m.created_at.isoformat()} for m in qs[:limit]]


def get_preview_link(actor: Actor, page_id: str, item_id: str | None = None) -> dict:
    page = _page(page_id)
    if item_id:
        _parse_item_id(item_id)
    return {"page": page["id"], "preview_url": preview_url(page["id"], item_id),
            "note": "Opens the CMS page editor with unpublished changes applied. The person must be signed in to the CMS."}


# --------------------------------------------------------------------------- writes
@transaction.atomic
def update_item(actor: Actor, item_id: str, fields: dict, expected_version: int) -> dict:
    page_id, view, resource, obj = _parse_item_id(item_id)
    data, images, photos, warnings = _prepare(actor, view, fields, creating=False)
    before = audit.row_values(obj)
    if obj.version != expected_version:  # also covers an images-only or photos-only change
        with _core():
            raise content.stale_error(resource, obj, expected_version)
    if data:
        with _core():
            obj = content.update_by_item_id(item_id, data, ctx=actor.ctx, expected_version=expected_version)
    obj = _attach_images(actor, resource, obj, images)
    _add_photos(actor, view, obj, photos)
    obj.refresh_from_db()
    return _result(page_id, item_id, obj, kind="changed", before=before, warnings=warnings)


@transaction.atomic
def create_item(actor: Actor, section_id: str, fields: dict) -> dict:
    """New rows start hidden (addendum A3): a Publisher reviews and shows them."""
    page, section = _section(section_id)
    if section["kind"] != "collection":
        raise CmsError("CMS_VALIDATION", f"{section['label']} is a single block; use update_section to change it.",
                       field="section")
    data, images, photos, warnings = _prepare(actor, section, fields, creating=True)
    resource = section["resource"]
    with _core():
        obj = content.create_item(resource, data, ctx=actor.ctx, section_id=section_id)
    obj = _attach_images(actor, resource, obj, images)
    _add_photos(actor, section, obj, photos)
    obj.refresh_from_db()
    item_id = make_item_id(section_id, resource, obj.pk)
    return _result(page["id"], item_id, obj, kind="added", before=None, warnings=warnings)


@transaction.atomic
def hide_item(actor: Actor, item_id: str, expected_version: int) -> dict:
    page_id, view, resource, obj = _parse_item_id(item_id)
    if view["kind"] != "collection" or not has_visibility(resource):
        raise CmsError("CMS_VALIDATION", f"{view.get('label', view['id'])} items can't be hidden; they can only be "
                       "removed in the CMS by a Publisher.", field="id")
    before = audit.row_values(obj)
    with _core():
        obj = content.update_by_item_id(item_id, {"is_published": False}, ctx=actor.ctx,
                                        expected_version=expected_version)
    return _result(page_id, item_id, obj, kind="hidden", before=before)


@transaction.atomic
def reorder(actor: Actor, section_id: str, item_ids: list[str]) -> dict:
    """Reorder a section's items, or one item's photos (send the child ids, e.g. media.events.media-event-images:3)."""
    page, section = _section(section_id)
    if section["kind"] != "collection":
        raise CmsError("CMS_VALIDATION", f"{section['label']} can't be reordered.", field="section")
    if not isinstance(item_ids, list) or not item_ids:
        raise CmsError("CMS_VALIDATION", "Send the full list of item ids in the new order.", field="ids")
    parsed = []
    for item_id in item_ids:
        _, view, resource, obj = _parse_item_id(item_id)
        if view["id"] != section["id"]:
            raise CmsError("CMS_VALIDATION", f"{item_id} is not in {section_id}.", field="ids")
        parsed.append((view, resource, obj))
    view, resource = parsed[0][0], parsed[0][1]
    if any(r != resource for _v, r, _o in parsed):
        raise CmsError("CMS_VALIDATION", "Reorder one list at a time (all ids of the same kind).", field="ids")
    qs = _queryset(view)
    if view.get("parent_field"):
        parents = {getattr(o, view["parent_field"] + "_id") for _v, _r, o in parsed}
        if len(parents) != 1:
            raise CmsError("CMS_VALIDATION", "Reorder the photos of one item at a time.", field="ids")
        qs = qs.filter(**{view["parent_field"]: parents.pop()})
    model = _model(resource)
    if not any(f.name == "order" for f in model._meta.fields):
        raise CmsError("CMS_VALIDATION", f"{section['label']} can't be reordered.", field="section")
    pks = [o.pk for _v, _r, o in parsed]
    existing = dict(qs.values_list("pk", "order"))
    if sorted(pks) != sorted(existing):
        missing = [make_item_id(section_id, resource, pk) for pk in existing if pk not in pks]
        raise CmsError("CMS_VALIDATION", "The list must contain every item of the list exactly once. "
                       f"Missing: {', '.join(missing) or 'none'}.", field="ids")
    with _core():
        content.reorder(resource, pks, ctx=actor.ctx, queryset=qs)
    after = dict(qs.values_list("pk", "order"))
    return {"id": section_id, "version": None, "page": page["id"], "label": section["label"],
            "preview_url": preview_url(page["id"]), "status": "draft", "kind": "reordered",
            "before": {str(k): v for k, v in existing.items()}, "after": {str(k): v for k, v in after.items()},
            "warnings": [], "deduplicated": False}


# --------------------------------------------------------------------------- discard
# Core's discard reverts an item to its last published values, whoever changed it. Claude must
# never throw away someone else's work, so before calling it we check the item's audit trail
# since the last publish: if only this caller's Claude changes are there, core's discard runs
# (it also removes rows Claude added); if others edited the item too, only Claude's own fields
# are put back — and only when nobody changed those fields after Claude. Otherwise
# CMS_STALE_VERSION and nothing changes.
_UNDO_IGNORED = {"id", "version"}


def _since():
    _data, snap = changes.baseline()
    return snap.created_at if snap else None


def _entries(resource: str, pk, since, section: dict | None):
    """Audit entries of a row since the last publish and since its last discard/restore (which reset it)."""
    qs = AuditEntry.objects.filter(resource=resource, pk_value=str(pk))
    if since:
        qs = qs.filter(at__gt=since)
    entries = list(qs.order_by("at", "id"))
    resets = [i for i, e in enumerate(entries) if e.action in ("discard", "restore")]
    if resets:
        entries = entries[resets[-1] + 1:]
    if section is not None and section["kind"] == "singleton":  # one row, several sections: only this one's fields
        names = registry.editable_fields(section)
        entries = [e for e in entries if audit.changed_fields(e.before, e.after, names)]
    return entries


def _discard_stale(item_id: str, current: int | None = None) -> CmsError:
    return CmsError("CMS_STALE_VERSION",
                    f"{item_id} was edited by someone else after Claude's change, so it can't be undone "
                    "automatically. Nothing was changed.",
                    fix="Tell the user to review this item in the CMS editor.", current_version=current, field="id")


def _undo_item(actor: Actor, item_id: str, *, session_only: bool) -> int:
    """Undo Claude's unpublished changes on one item (see above). Returns how many changes were undone."""
    try:
        _page_id, view, resource, pk = registry.view_for_item(item_id)
    except ValueError:
        raise CmsError("CMS_NOT_FOUND", f"{item_id!r} is not a content id.", field="id") from None
    since = _since()
    entries = _entries(resource, pk, since, view)

    def mine(e):
        if e.channel != "mcp" or e.actor_id != actor.user.pk:
            return False
        return e.connector_session == actor.session_key[:64] if session_only else True

    own = [e for e in entries if mine(e)]
    if not own:
        raise CmsError("CMS_NOT_FOUND", f"There is no unpublished change from Claude on {item_id}.",
                       fix="Changes made in the CMS editor can be discarded there.", field="id")
    foreign = [e for e in entries if not mine(e)]
    model = _model(resource)
    obj = model.objects.select_for_update().filter(pk=pk).first()
    if obj is not None and not foreign:
        # A change that bypassed the audit log (shell, data fix) counts as someone else's edit.
        last = own[-1].after or {}
        now = audit.row_values(obj)
        names = registry.editable_fields(view) if view["kind"] == "singleton" else now.keys()
        if any(now.get(k) != last.get(k) for k in names if k not in _UNDO_IGNORED and k in last):
            foreign = ["unaudited"]
    if not foreign and since is not None:
        with _core():
            changes.discard_item(item_id, ctx=actor.ctx)
        return len(own)
    if obj is None:
        raise CmsError("CMS_NOT_FOUND", f"{item_id} no longer exists.", field="id")
    if any(e.action == "create" for e in own):
        if foreign:
            raise _discard_stale(item_id, obj.version)
        # Nothing published yet to compare against: hide the row Claude added rather than delete it.
        with _core():
            content.update_item(resource, pk, {"is_published": False}, ctx=actor.ctx, expected_version=obj.version)
        return len(own)
    # Field by field: what Claude changed, as it was before Claude's first change to that field.
    first_before, last_after = {}, {}
    for e in own:
        for f in audit.changed_fields(e.before, e.after):
            if f["name"] in _UNDO_IGNORED:
                continue
            first_before.setdefault(f["name"], f["before"])
            last_after[f["name"]] = f["after"]
    now = audit.row_values(obj)
    if any(now.get(k) != v for k, v in last_after.items()):
        raise _discard_stale(item_id, obj.version)
    restore = {k: first_before[k] for k in last_after}
    files = [k for k in restore if model._meta.get_field(k).get_internal_type() in ("ImageField", "FileField")]
    if files:
        raise CmsError("CMS_STALE_VERSION",
                       f"{item_id} was also edited by someone else, and Claude's photo change can't be undone "
                       "separately. Nothing was changed.",
                       fix="Tell the user to put the earlier photo back in the CMS editor.",
                       current_version=obj.version, field=files[0])
    if restore:
        with _core():
            content.update_item(resource, pk, restore, ctx=actor.ctx, expected_version=obj.version)
    return len(own)


def _expand(actor: Actor, item_id: str, *, session_only: bool) -> list[str]:
    """A section id (after `reorder`) stands for every row of it that Claude moved."""
    if str(item_id) not in registry.section_index():
        return [item_id]
    qs = AuditEntry.objects.filter(channel="mcp", actor=actor.user, action="reorder",
                                   item_id__startswith=f"{item_id}.")
    if session_only:
        qs = qs.filter(connector_session=actor.session_key[:64])
    since = _since()
    if since:
        qs = qs.filter(at__gt=since)
    ids = list(dict.fromkeys(qs.order_by("id").values_list("item_id", flat=True)))
    if not ids:
        raise CmsError("CMS_NOT_FOUND", f"There is no unpublished change from Claude on {item_id}.",
                       fix="Changes made in the CMS editor can be discarded there.", field="id")
    return ids


def _mark_discarded(actor: Actor, item_ids, *, session_only: bool):
    qs = ConnectorWrite.objects.filter(session__user=actor.user, discarded=False)
    if session_only:
        qs = qs.filter(session__key=actor.session_key)
    prefixes = tuple(f"{i}." for i in item_ids)
    for w in qs:
        if w.item_id in item_ids or w.item_id.startswith(prefixes) or any(i.startswith(f"{w.item_id}.") for i in item_ids):
            # Free the de-duplication key: after a discard, the same create is a new change again.
            ConnectorWrite.objects.filter(pk=w.pk).update(discarded=True, dedupe_key=None)


@transaction.atomic
def discard_change(actor: Actor, item_id: str) -> dict:
    targets = _expand(actor, str(item_id or ""), session_only=False)
    undone = sum(_undo_item(actor, t, session_only=False) for t in targets)
    _mark_discarded(actor, [str(item_id), *targets], session_only=False)
    return {"id": item_id, "discarded": undone, "status": "draft"}


@transaction.atomic
def discard_session(actor: Actor) -> dict:
    """Undo every change of this conversation. All or nothing: if one item can't be undone, none is."""
    qs = AuditEntry.objects.filter(channel="mcp", actor=actor.user, connector_session=actor.session_key[:64]) \
        .exclude(action__in=["discard", "restore"])
    since = _since()
    if since:
        qs = qs.filter(at__gt=since)
    item_ids = list(dict.fromkeys(qs.order_by("-at", "-id").values_list("item_id", flat=True)))
    undone, done = 0, []
    for iid in item_ids:  # newest first, so child rows go before the rows they belong to
        try:
            undone += _undo_item(actor, iid, session_only=True)
            done.append(iid)
        except CmsError as err:
            if err.code != "CMS_NOT_FOUND":
                raise  # rolls back everything undone so far
    _mark_discarded(actor, done, session_only=True)
    return {"discarded": undone, "items": done, "status": "draft"}


# --------------------------------------------------------------------------- photos, review
def request_upload_link(actor: Actor) -> dict:
    with _core():
        link = uploads.create_upload_link(actor.user, ctx=actor.ctx)
    expires = link["expires_at"]
    return {"upload_url": link["url"], "expires_at": expires.isoformat() if hasattr(expires, "isoformat") else expires}


def fetch_image_from_url(actor: Actor, url: str, *, resolver=None, connector=None) -> dict:
    data, _source = fetch_image_bytes(url, resolver=resolver, connector=connector)
    processed = process_image(data)
    asset, deduplicated = uploads.save_media(processed, user=actor.user)
    return {"media_id": f"media:{asset.pk}", "width": asset.width, "height": asset.height,
            "url": _media_url(asset.file.name), "deduplicated": deduplicated}


def request_review(actor: Actor, note: str) -> dict:
    note = _CONTROL.sub("", str(note or "")).strip()[:1000]
    with _core():
        rr = review.request_review(actor.user, note, ctx=actor.ctx)
    # The email goes out when the caller's transaction commits; read rr.notice after that (tools.request_review).
    return {"notified": len(rr.notice.recipients), "status": "waiting_for_review", "_notice": rr.notice}


def describe_item(actor: Actor, item_id: str) -> dict:
    page_id, _view, _resource, obj = _parse_item_id(item_id)
    return {"id": item_id, "version": version_of(obj), "page": page_id, "label": _label(obj),
            "preview_url": preview_url(page_id, item_id), "status": "draft", "kind": None, "warnings": []}
