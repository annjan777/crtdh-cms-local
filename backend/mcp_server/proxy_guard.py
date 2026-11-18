"""Trusted-proxy guard for the whole MCP ASGI app (Starlette routes included).

Same rule as backend-security's Django TrustedProxyMiddleware, which the Starlette routes
(/mcp, /.well-known/*) never pass through: only the gateway and cloudflared (TRUSTED_PROXY_IPS)
may talk to this process or set forwarding headers. A peer outside that list loses every
forwarding header, and with REQUIRE_TRUSTED_PROXY it is refused with 403, so a process that
reaches the container directly can't bypass Cloudflare's WAF (Anthropic's IP range) or the
tunnel's path allow-list. uvicorn must run with --no-proxy-headers so the peer address is the
real TCP peer.
"""

from __future__ import annotations

import ipaddress
import logging

from django.conf import settings
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("crtdh.security")

FORWARDING_HEADERS = frozenset({
    b"cf-connecting-ip", b"x-forwarded-proto", b"x-forwarded-for", b"x-forwarded-host", b"x-real-ip", b"forwarded",
})

try:
    from apps.common.middleware import peer_is_trusted  # type: ignore  (backend-security)
except ImportError:  # TODO(integration, backend-security): always importable after their merge

    def peer_is_trusted(ip):
        try:
            addr = ipaddress.ip_address((ip or "").strip())
        except ValueError:
            return False
        nets = []
        for spec in getattr(settings, "TRUSTED_PROXY_IPS", []):
            try:
                nets.append(ipaddress.ip_network(spec.strip(), strict=False))
            except ValueError:
                continue
        return any(addr in net for net in nets)


class TrustedProxyGuard:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        peer = (scope.get("client") or ("", 0))[0]
        if not peer_is_trusted(peer):
            if getattr(settings, "REQUIRE_TRUSTED_PROXY", False):
                logger.warning("refused direct request peer=%s path=%s", peer, scope.get("path", "")[:200])
                if scope["type"] == "http":
                    await send({"type": "http.response.start", "status": 403,
                                "headers": [(b"content-type", b"text/plain"), (b"content-length", b"0")]})
                    await send({"type": "http.response.body", "body": b""})
                else:
                    await send({"type": "websocket.close", "code": 1008})
                return
            scope = {**scope, "headers": [(k, v) for k, v in scope.get("headers", []) if k.lower() not in FORWARDING_HEADERS]}
        await self.app(scope, receive, send)
