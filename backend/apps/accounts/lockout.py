"""Sign-in lockout with exponential backoff, per username and per IP.

Counters live in the database so every gunicorn worker sees the same state.
After THRESHOLD failures a key is locked for BASE * 2**(n - THRESHOLD) seconds,
capped at MAX. Counters reset after RESET_AFTER seconds without failures, and
a successful sign-in clears the username counter.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AuthThrottle

logger = logging.getLogger("crtdh.security")


def keys_for(username, ip):
    keys = []
    if username:
        keys.append("u:" + username.strip().lower()[:150])
    if ip:
        keys.append("ip:" + ip)
    return keys


def _cfg():
    return settings.AUTH_LOCKOUT


def retry_after(keys):
    """Seconds until every key is unlocked (0 if none is locked)."""
    now = timezone.now()
    waits = [
        (t.locked_until - now).total_seconds()
        for t in AuthThrottle.objects.filter(key__in=keys, locked_until__gt=now)
    ]
    return int(max(waits)) + 1 if waits else 0


def register_failure(keys):
    cfg = _cfg()
    now = timezone.now()
    with transaction.atomic():
        for key in keys:
            t, _ = AuthThrottle.objects.select_for_update().get_or_create(key=key)
            if t.updated_at and (now - t.updated_at).total_seconds() > cfg["RESET_AFTER_SECONDS"]:
                t.failures = 0
            t.failures += 1
            threshold = cfg["IP_THRESHOLD"] if key.startswith("ip:") else cfg["USER_THRESHOLD"]
            if t.failures >= threshold:
                secs = min(cfg["BASE_SECONDS"] * 2 ** (t.failures - threshold), cfg["MAX_SECONDS"])
                t.locked_until = now + timedelta(seconds=secs)
                logger.warning("auth lockout key=%s failures=%s seconds=%s", key, t.failures, secs)
            t.save()


def clear(username):
    AuthThrottle.objects.filter(key__in=keys_for(username, None)).delete()
