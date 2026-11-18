"""Cloudflare Turnstile server-side check (fixed endpoint, never user-controlled)."""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger("crtdh.security")
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify(token, remote_ip=None):
    """True if Turnstile accepts `token`. Without TURNSTILE_SECRET: allowed only in DEBUG."""
    secret = settings.TURNSTILE_SECRET
    if not secret:
        if settings.DEBUG:
            logger.warning("TURNSTILE_SECRET not set: skipping Turnstile check (DEBUG only)")
            return True
        logger.error("TURNSTILE_SECRET not set in production: rejecting contact message")
        return False
    if not token or not isinstance(token, str) or len(token) > 2048:
        return False
    body = {"secret": secret, "response": token}
    if remote_ip:
        body["remoteip"] = remote_ip
    req = urllib.request.Request(VERIFY_URL, data=urllib.parse.urlencode(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310 - constant https URL
            return bool(json.loads(resp.read(65536)).get("success"))
    except Exception:
        logger.exception("Turnstile verification failed to complete")
        return False
