"""Keeping a long OAuth authorization request under a short key.

Some hosts (academicweb's firewall) refuse any URL whose query string is longer than about 270 characters, and
Claude's authorization request is longer. A static relay page elsewhere moves the query into the path
(/oauth/go/<base64url>); oauth_go keeps it in the cache for RELAY_SECONDS under a random key, and the consent view
reads it back from ?k=<key>. The request is only stored after its client and redirect URI are checked, so this
can't be used to keep arbitrary data, and the consent view still runs every normal OAuth check on it.
"""

import base64
import binascii
import secrets
from urllib.parse import parse_qs

from django.core.cache import cache

RELAY_SECONDS = 15 * 60
MAX_QUERY = 4096
_PREFIX = "oauth-relay:"


def decode(payload: str) -> str | None:
    if not payload or len(payload) > MAX_QUERY * 2:
        return None
    try:
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        query = raw.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    if len(query) > MAX_QUERY or any(ord(c) < 0x20 for c in query):
        return None
    return query


def valid_request(query: str) -> bool:
    from oauth2_provider.models import get_application_model

    params = parse_qs(query, keep_blank_values=True)
    one = {k: v[0] for k, v in params.items() if len(v) == 1}
    if one.get("response_type") != "code" or not one.get("client_id") or not one.get("redirect_uri"):
        return False
    app = get_application_model().objects.filter(client_id=one["client_id"][:100]).first()
    return app is not None and app.redirect_uri_allowed(one["redirect_uri"])


def store(query: str) -> str:
    key = secrets.token_urlsafe(16)
    cache.set(_PREFIX + key, query, RELAY_SECONDS)
    return key


def load(key: str) -> str | None:
    if not key or len(key) > 64:
        return None
    return cache.get(_PREFIX + key)
