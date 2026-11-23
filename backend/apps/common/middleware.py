import ipaddress
import logging
import uuid
from functools import lru_cache

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger("crtdh.security")
FORWARDING_HEADERS = ("HTTP_CF_CONNECTING_IP", "HTTP_X_FORWARDED_PROTO", "HTTP_X_FORWARDED_FOR",
                      "HTTP_X_FORWARDED_HOST", "HTTP_X_REAL_IP", "HTTP_FORWARDED")


@lru_cache(maxsize=8)
def _networks(spec):
    return tuple(ipaddress.ip_network(s.strip(), strict=False) for s in spec if s.strip())


def peer_is_trusted(ip):
    """True if `ip` (the TCP peer, REMOTE_ADDR) is one of settings.TRUSTED_PROXY_IPS (IPs or CIDRs):
    the gateway nginx and cloudflared on the compose network. Usable from ASGI code too."""
    try:
        addr = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return False
    return any(addr in net for net in _networks(tuple(settings.TRUSTED_PROXY_IPS)))


class TrustedProxyMiddleware:
    """First middleware. Requests whose TCP peer is not a trusted proxy lose every forwarding header
    (so CF-Connecting-IP / X-Forwarded-Proto cannot be forged), and with REQUIRE_TRUSTED_PROXY they are
    refused outright: in production only the gateway and cloudflared may talk to the app, so a process
    that reaches the container directly cannot bypass Cloudflare Access, the WAF or the path allow-lists."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        peer = request.META.get("REMOTE_ADDR", "")
        if not peer_is_trusted(peer):
            if settings.REQUIRE_TRUSTED_PROXY:
                logger.warning("refused direct request peer=%s path=%s", peer, request.path[:200])
                return HttpResponseForbidden(b"", content_type="text/plain")
            for key in FORWARDING_HEADERS:
                request.META.pop(key, None)
        elif getattr(settings, "FORWARDED_PROTO_DEFAULT", "") and "HTTP_X_FORWARDED_PROTO" not in request.META:
            request.META["HTTP_X_FORWARDED_PROTO"] = settings.FORWARDED_PROTO_DEFAULT
        return self.get_response(request)


class RequestIdMiddleware:
    """Gives every request an id (echoed as X-Request-ID and in error bodies)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class SecurityHeadersMiddleware:
    """CSP and Permissions-Policy (SecurityMiddleware covers HSTS, nosniff, Referrer-Policy)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        response.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith("/api/"):
            response.setdefault("Cache-Control", "no-store")
        return response


def client_ip(request):
    """The caller's IP. CF-Connecting-IP is honoured only when TRUST_CF_CONNECTING_IP is on AND the TCP
    peer is a trusted proxy (gateway/cloudflared); otherwise the peer address itself."""
    if settings.TRUST_CF_CONNECTING_IP and peer_is_trusted(request.META.get("REMOTE_ADDR", "")):
        ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
        if ip:
            return ip
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False) and peer_is_trusted(request.META.get("REMOTE_ADDR", "")):
        last = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[-1].strip()
        try:
            return str(ipaddress.ip_address(last))
        except ValueError:
            pass
    return request.META.get("REMOTE_ADDR", "")
