"""Load a snapshot-shaped JSON (contract §1 / stub-snapshot.json) into the DB.

Generic: resource name -> model is read from the DRF router in config/urls.py, so new
resources work without changes here. Unknown keys (serializer-only fields such as
`category_name`) are skipped; FK fields are written as `<field>_id`; absolute media URLs
become storage-relative paths.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

from django.db import models

SAMPLE_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "sample_snapshot.json"
SINGLETON_MODELS = {"site-settings": "core.SiteSettings", "about-page": "core.AboutPage", "home-page": "core.HomePage"}


def resource_models():
    from django.apps import apps as django_apps

    from config.urls import router

    out = {}
    for prefix, viewset, _basename in router.registry:
        qs = getattr(viewset, "queryset", None)
        if qs is not None:
            out[prefix] = qs.model
    for key, label in SINGLETON_MODELS.items():
        out[key] = django_apps.get_model(label)
    return out


def _media_path(value):
    if not value or not isinstance(value, str):
        return value
    path = urlparse(value).path if "://" in value else value
    return path.split("/media/", 1)[1] if "/media/" in path else path.lstrip("/")


def _kwargs(model, row):
    fields = {f.name: f for f in model._meta.concrete_fields}
    kw = {}
    for key, value in row.items():
        f = fields.get(key)
        if f is None:
            continue
        if isinstance(f, models.ForeignKey):
            kw[f.attname] = value
        elif isinstance(f, models.FileField):
            kw[key] = _media_path(value) or ""
        elif value is None and not f.null:
            continue
        else:
            kw[key] = value
    return kw


# parents before children
ORDER_HINT = ["team-categories", "innovations", "products", "media-events", "image-grid-blocks"]


def load_snapshot_into_db(path=SAMPLE_SNAPSHOT_PATH, exclude=()):
    data = json.loads(Path(path).read_text())
    mapping = resource_models()
    counts = {}
    for key, row in data.get("singletons", {}).items():
        model = mapping[key]
        model.objects.update_or_create(pk=row.get("id", 1), defaults=_kwargs(model, row))
        counts[key] = 1
    names = sorted(data["collections"], key=lambda k: (k not in ORDER_HINT, ORDER_HINT.index(k) if k in ORDER_HINT else 0))
    for key in names:
        if key in exclude or key not in mapping:
            continue
        model = mapping[key]
        objs = [model(**_kwargs(model, row)) for row in data["collections"][key]]
        model.objects.bulk_create(objs)
        counts[key] = len(objs)
    return counts


def load_sample_content():
    return load_snapshot_into_db(SAMPLE_SNAPSHOT_PATH)
