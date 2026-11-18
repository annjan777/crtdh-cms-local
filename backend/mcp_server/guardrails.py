"""Blast-radius limits for Claude (PLAN WS4.5): per-user rate limits, a change cap per
connector session, and de-duplication of repeated creates."""

from __future__ import annotations

import hashlib
import json
import time

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from .errors import CmsError
from .models import ConnectorSession, ConnectorWrite

# Natural keys per resource: a second create with the same values in the same connector
# session returns the first record instead of a duplicate.
NATURAL_KEYS = {
    "team-members": ["name"],
    "media-events": ["title", "event_date"],
    "news-items": ["text"],
    "hero-slides": ["image", "heading"],
    "media-coverage-links": ["url"],
    "innovations": ["title"],
    "equipment": ["name"],
    "services": ["title"],
    "enterprises": ["name"],
    "products": ["name"],
}


def check_rate(user_id: int, *, write: bool):
    minute = int(time.time() // 60)
    checks = [("all", settings.MCP_RATE_LIMIT_PER_MINUTE)]
    if write:
        checks.append(("write", settings.MCP_WRITE_RATE_LIMIT_PER_MINUTE))
    for kind, limit in checks:
        key = f"mcp-rate:{kind}:{user_id}:{minute}"
        cache.add(key, 0, timeout=120)
        try:
            count = cache.incr(key)
        except ValueError:  # evicted between add and incr
            cache.set(key, 1, timeout=120)
            count = 1
        if count > limit:
            raise CmsError(
                "CMS_RATE_LIMITED",
                f"Too many {'changes' if kind == 'write' else 'requests'} in one minute (limit {limit}). Nothing was changed.",
            )


def session_for(user, key: str) -> ConnectorSession:
    session, _ = ConnectorSession.objects.get_or_create(key=key, defaults={"user": user})
    if session.user_id != user.pk:  # the SDK binds sessions to a token principal; belt and braces
        raise CmsError("CMS_UNAUTHENTICATED", "This connector session belongs to someone else.")
    return session


def check_session_limit(session: ConnectorSession):
    limit = settings.CMS_SESSION_LIMIT
    if session.change_count >= limit:
        raise CmsError(
            "CMS_SESSION_LIMIT",
            f"This conversation has already made {session.change_count} changes, the most allowed in one session "
            f"({limit}). Nothing was changed.",
        )


def dedupe_key(resource: str, fields: dict, idempotency_key: str | None) -> str:
    if idempotency_key:
        basis = {"idempotency_key": str(idempotency_key)[:200]}
    else:
        names = NATURAL_KEYS.get(resource)
        basis = {n: fields.get(n) for n in names} if names and any(fields.get(n) for n in names) else fields
        basis = {"resource": resource, **basis}
    blob = json.dumps(basis, sort_keys=True, default=str).casefold().encode()
    return hashlib.sha256(blob).hexdigest()


def previous_create(session: ConnectorSession, key: str) -> ConnectorWrite | None:
    return ConnectorWrite.objects.filter(session=session, dedupe_key=key, discarded=False).first()


def record_write(session: ConnectorSession, result: dict, key: str | None = None):
    ConnectorWrite.objects.create(
        session=session, item_id=result["id"], kind=result["kind"],
        before=result.get("before"), after=result.get("after"), dedupe_key=key,
    )
    ConnectorSession.objects.filter(pk=session.pk).update(change_count=F("change_count") + 1)
