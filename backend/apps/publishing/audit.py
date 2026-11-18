"""Audit log (contract §3, plan WS1.4). Every content write goes through record()."""
import json
from dataclasses import dataclass

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.crypto import constant_time_compare

from .models import AuditEntry

CHANNELS = {"admin", "mcp", "api"}


@dataclass
class WriteContext:
    """Who is writing and through what. MCP builds this in-process (channel="mcp", connector_session=...)."""

    user: object = None
    channel: str = "admin"
    connector_session: str | None = None

    def __post_init__(self):
        if self.channel not in CHANNELS:
            raise ValueError(f"unknown channel {self.channel!r}")


def context_from_request(request):
    """Browsers always count as the admin channel. X-CMS-Channel is honoured only for a caller that also sends
    X-CMS-Internal equal to settings.CMS_INTERNAL_SECRET (unset = never)."""
    channel, session = "admin", None
    secret = getattr(settings, "CMS_INTERNAL_SECRET", "")
    supplied = request.META.get("HTTP_X_CMS_INTERNAL", "")
    if secret and supplied and constant_time_compare(secret, supplied):
        wanted = request.META.get("HTTP_X_CMS_CHANNEL", "").strip().lower()
        if wanted in CHANNELS:
            channel = wanted
        session = request.META.get("HTTP_X_CMS_CONNECTOR_SESSION") or None
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    return WriteContext(user=user, channel=channel, connector_session=session)


def jsonable(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def row_values(obj):
    """Raw stored values of a row (FKs as ids, files as storage names) — the audit before/after shape."""
    if obj is None:
        return None
    out = {}
    for field in obj._meta.concrete_fields:
        value = getattr(obj, field.attname)
        if isinstance(field, models.FileField):
            value = value.name if value else ""
        out[field.name] = value
    return jsonable(out)


def record(ctx, action, resource, pk, before=None, after=None, item_id=""):
    user = ctx.user if ctx and ctx.user is not None and getattr(ctx.user, "pk", None) else None
    return AuditEntry.objects.create(
        actor=user,
        actor_name=user.get_username() if user else "",
        channel=ctx.channel if ctx else "api",
        connector_session=ctx.connector_session if ctx else None,
        item_id=item_id or "",
        resource=resource,
        pk_value=str(pk) if pk is not None else "",
        action=action,
        before=before,
        after=after,
    )


def last_entry(resource, pk, fields=None, since=None):
    """Latest audit entry for a row; with `fields`, the latest one that changed any of them."""
    qs = AuditEntry.objects.filter(resource=resource, pk_value=str(pk)).select_related("actor")
    if since:
        qs = qs.filter(at__gt=since)
    for entry in qs.order_by("-at", "-id")[:50]:
        if not fields:
            return entry
        b, a = entry.before or {}, entry.after or {}
        if any(b.get(name) != a.get(name) for name in fields):
            return entry
    return None


ACTION_VERBS = {"create": "added", "update": "changed", "delete": "removed", "reorder": "moved",
                "discard": "discarded", "restore": "restored"}


def changed_fields(before, after, only=None):
    """[{name, before, after}] for the keys that differ (version ignored); `only` limits to a field set."""
    b, a = before or {}, after or {}
    names = [k for k in dict.fromkeys([*b, *a]) if k not in ("version", "id")]
    if only is not None:
        names = [k for k in names if k in only]
    return [{"name": k, "before": b.get(k), "after": a.get(k)} for k in names if b.get(k) != a.get(k)]


def serialize_entry(e, only=None):
    """Addendum A8 entry {item_id, at, author, channel, action, fields} plus raw details (actor, before, after)."""
    fields = changed_fields(e.before, e.after, only) if e.before is not None and e.after is not None else []
    verb = ACTION_VERBS.get(e.action, e.action)
    if e.action == "update" and any(f["name"] == "is_published" for f in fields):
        verb = "hid" if (e.after or {}).get("is_published") is False else "showed"
    return {
        "item_id": e.item_id,
        "at": e.at,
        "author": e.actor_name or None,
        "channel": e.channel,
        "action": verb,
        "fields": fields,
        "session_id": e.connector_session,
        "raw_action": e.action,
        "id": e.id,
        "actor": e.actor_name or None,
        "connector_session": e.connector_session,
        "resource": e.resource,
        "pk": e.pk_value,
        "before": e.before,
        "after": e.after,
    }
