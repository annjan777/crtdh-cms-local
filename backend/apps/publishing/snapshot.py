"""Snapshot (contract §1): the whole public site's content as one JSON document.

build_snapshot() reads the CMS database through the existing DRF list serializers (so row shapes stay what the
public pages already use), keeps only visible rows, sorts by order then id, and rewrites every media URL to a
content-hashed site path `/media/<sha256[:16]>.<ext>` listed in `media`.
"""
import hashlib
import json
import logging
import os
from datetime import UTC
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import serializers as drf_serializers

from . import registry

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("snapshot.schema.json")
RASTER_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VARIANT_WIDTHS = (480, 960, 1600, 2400)


# ---- media hashing ---------------------------------------------------------------------------------------------
_hash_cache = {}


def _file_info(path):
    """(sha256 hex, width, height) for a file; cached on (path, size, mtime)."""
    st = os.stat(path)
    key = (str(path), st.st_size, st.st_mtime_ns)
    hit = _hash_cache.get(key)
    if hit:
        return hit
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    width = height = None
    if Path(path).suffix.lower() in RASTER_EXTS | {".gif"}:
        try:
            from PIL import Image

            with Image.open(path) as im:
                width, height = im.size
        except Exception:  # noqa: BLE001 - not an image after all
            pass
    _hash_cache[key] = (h.hexdigest(), width, height)
    return _hash_cache[key]


@lru_cache(maxsize=1)
def avif_supported():
    try:
        from PIL import features

        return bool(features.check("avif"))
    except Exception:  # noqa: BLE001
        return False


def media_entry(source, sha, width, height):
    ext = Path(source).suffix.lower()
    h16 = sha[:16]
    variants = {"avif": [], "webp": []}
    if ext in RASTER_EXTS and width:
        widths = [w for w in VARIANT_WIDTHS if w < width]
        variants["webp"] = [{"url": f"/media/{h16}-{w}.webp", "width": w} for w in widths]
        if avif_supported():
            variants["avif"] = [{"url": f"/media/{h16}-{w}.avif", "width": w} for w in widths]
    return f"/media/{h16}{ext}", {"source": source, "width": width, "height": height, "variants": variants}


class _MediaRewriter:
    def __init__(self, hashed=True):
        self.hashed = hashed
        self.media = {}
        self.warnings = []
        self.prefix = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else "/" + settings.MEDIA_URL

    def source_of(self, value):
        if isinstance(value, str) and value.startswith(self.prefix) and len(value) > len(self.prefix):
            return value[len(self.prefix):]
        return None

    def __call__(self, value):
        if isinstance(value, dict):
            return {k: self(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self(v) for v in value]
        source = self.source_of(value)
        if source is None or not self.hashed:
            return value
        path = Path(settings.MEDIA_ROOT) / source
        if not path.is_file():
            self.warnings.append(f"missing media file {source}")
            return None  # same as an empty file field, so the public page simply omits the image
        sha, w, h = _file_info(path)
        key, entry = media_entry(source, sha, w, h)
        self.media[key] = entry
        return key


# ---- reading the DB ---------------------------------------------------------------------------------------------
def _nested_prefetches(serializer_class, include_hidden):
    out = []
    for name, field in serializer_class().fields.items():
        if isinstance(field, drf_serializers.ListSerializer):
            child_model = field.child.Meta.model
            qs = child_model.objects.all()
            if not include_hidden and any(f.name == "is_published" for f in child_model._meta.concrete_fields):
                qs = qs.filter(is_published=True)
            order = ["order", "id"] if any(f.name == "order" for f in child_model._meta.concrete_fields) else ["id"]
            out.append(Prefetch(field.source or name, queryset=qs.order_by(*order)))
    return out


def queryset_for(resource, include_hidden=False):
    res = registry.RESOURCES[resource]
    model = res.model_class
    qs = model.objects.all()
    if not include_hidden:
        if res.has_visibility:
            qs = qs.filter(is_published=True)
        for parent in res.parents:
            parent_model = model._meta.get_field(parent).related_model
            if any(f.name == "is_published" for f in parent_model._meta.concrete_fields):
                qs = qs.filter(**{f"{parent}__is_published": True})
    order = ["order", "id"] if any(f.name == "order" for f in model._meta.concrete_fields) else ["id"]
    return qs.prefetch_related(*_nested_prefetches(res.serializer_class, include_hidden)).order_by(*order)


def serialize_resource(resource, include_hidden=False, request=None):
    res = registry.RESOURCES[resource]
    context = {"request": request} if request is not None else {}
    if res.kind == "singleton":
        return res.serializer_class(res.model_class.load(), context=context).data
    return res.serializer_class(queryset_for(resource, include_hidden), many=True, context=context).data


def collect(include_hidden=False, request=None, resources=None):
    """Plain serializer output (media URLs as the serializer renders them)."""
    names = resources or list(registry.RESOURCES)
    data = {"singletons": {}, "collections": {}}
    for name in names:
        key = "singletons" if registry.RESOURCES[name].kind == "singleton" else "collections"
        data[key][name] = json.loads(json.dumps(serialize_resource(name, include_hidden, request), default=str))
    return data


def canonical_json(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(snapshot):
    keys = ("singletons", "collections", "media", "registry")
    return hashlib.sha256(canonical_json({k: snapshot.get(k) for k in keys}).encode()).hexdigest()


def build_snapshot(published_by=None, now=None):
    """The snapshot dict, contract §1. Pure read; nothing is written."""
    now = now or timezone.now()
    raw = collect(include_hidden=False)
    rewrite = _MediaRewriter(hashed=True)
    singletons = rewrite(raw["singletons"])
    collections = rewrite(raw["collections"])
    published_at = now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": "",
        "published_at": published_at,
        "published_by": getattr(published_by, "username", published_by) or None,
        "singletons": singletons,
        "collections": collections,
        "registry": registry.export_registry(),
        "media": dict(sorted(rewrite.media.items())),
    }
    if rewrite.warnings:
        snap["warnings"] = sorted(set(rewrite.warnings))
    snap["snapshot_id"] = f"{published_at}-{content_hash(snap)[:6]}"
    return snap


def preview(page_id, request=None):
    """Snapshot-shaped data for one page from the current DB (admin canvas). Media stay CMS URLs."""
    page = registry.get_page(page_id)
    if page is None:
        return None
    names = {s["resource"] for s in page["sections"]} | {s["resource"] for s in registry.GLOBALS}
    # Pages that borrow other resources (stats on Home, page banners from hero slides).
    names |= {"home": {"team-members", "innovations", "enterprises"}, "team": {"hero-slides"},
              "media": {"hero-slides"}}.get(page_id, set())
    ordered = [n for n in registry.RESOURCES if n in names]
    data = collect(include_hidden=False, request=request, resources=ordered)
    return {"schema_version": SCHEMA_VERSION, "page": page_id, **data}


# ---- schema ---------------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def validate(snapshot):
    """List of human-readable schema errors (empty = valid)."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(schema())
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(snapshot), key=lambda e: list(map(str, e.absolute_path)))]
