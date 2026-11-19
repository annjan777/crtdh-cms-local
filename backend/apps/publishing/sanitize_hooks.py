"""Sanitise on every write path: a pre_save hook on every content model (serializer saves, MCP writes, discard,
restore, Django admin). Rich text is cleaned with apps.common.sanitize; an unsafe link is refused (CMS_VALIDATION)."""
from functools import cache

from django.db import models
from django.db.models.signals import pre_save

from apps.common.sanitize import clean_richtext, safe_url

from . import registry
from .errors import CMSError


@cache
def field_rules():
    """{model: (richtext field names, url field names)} from the registry plus every models.URLField."""
    rules = {}
    for _page, view in registry.all_views():
        model = registry.RESOURCES[view["resource"]].model_class
        rich, urls = rules.setdefault(model, (set(), set()))
        for fd in view["fields"]:
            if fd["type"] == "richtext":
                rich.add(fd["name"])
            elif fd["type"] == "url":
                urls.add(fd["name"])
    for res in registry.RESOURCES.values():
        model = res.model_class
        rich, urls = rules.setdefault(model, (set(), set()))
        urls.update(f.name for f in model._meta.concrete_fields if isinstance(f, models.URLField))
    return {m: (frozenset(r), frozenset(u)) for m, (r, u) in rules.items() if r or u}


def sanitise_instance(instance, raw=False):
    rich, urls = field_rules().get(type(instance), ((), ()))
    for name in rich:
        value = getattr(instance, name, None)
        if value:
            setattr(instance, name, clean_richtext(value))
    if raw:
        return
    for name in urls:
        if not safe_url(getattr(instance, name, None)):
            raise CMSError("CMS_VALIDATION", "This link is not allowed. Use a web address starting with https://, "
                           "a mailto: address, or a page on this site such as /about.", field=name,
                           fix="Replace the link; javascript:, data: and //host links are refused.")


def _pre_save(sender, instance, raw=False, **kwargs):
    sanitise_instance(instance, raw=raw)


def connect():
    for model in field_rules():
        pre_save.connect(_pre_save, sender=model, dispatch_uid=f"crtdh-sanitise-{model._meta.label}")
