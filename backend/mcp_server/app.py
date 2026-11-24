"""The MCP hostname's ASGI application.

Only these paths exist; everything else is 404:
  /mcp                                         MCP streamable HTTP (OAuth bearer required)
  /.well-known/oauth-protected-resource[/mcp]  RFC 9728
  /.well-known/oauth-authorization-server      RFC 8414
  /oauth/...                                   django-oauth-toolkit (token, revoke, authorize)
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.streamable_http_manager import StreamableHTTPASGIApp, StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from .auth import DjangoTokenVerifier
from .tools import build_server

WELL_KNOWN = (
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/mcp",
    "/.well-known/oauth-authorization-server",
)


class OAuthDjangoApp(ASGIHandler):
    """Django, but resolving only mcp_server.urls (OAuth + metadata), whatever ROOT_URLCONF says."""

    async def get_response_async(self, request):
        request.urlconf = "mcp_server.urls"
        return await super().get_response_async(request)


class ProtocolVersionGuard:
    """Refuse MCP protocol revisions this server hasn't been tested with (see docs/mcp.md)."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        version = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"mcp-protocol-version"), None)
        if version is not None and version not in settings.MCP_PROTOCOL_VERSIONS:
            body = json.dumps({"jsonrpc": "2.0", "id": None, "error": {
                "code": -32600,
                "message": f"Unsupported MCP-Protocol-Version {version[:40]!r}; this server supports "
                           f"{', '.join(settings.MCP_PROTOCOL_VERSIONS)}."}}).encode()
            await send({"type": "http.response.start", "status": 400,
                        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


async def not_found(request: Request, exc=None):
    return JSONResponse({"error": "not_found"}, status_code=404)


def _security_settings() -> TransportSecuritySettings:
    host = urlsplit(settings.MCP_PUBLIC_URL).netloc
    hosts = [host, *getattr(settings, "MCP_EXTRA_ALLOWED_HOSTS", [])]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=["https://claude.ai", "https://claude.com",
                         "{0.scheme}://{0.netloc}".format(urlsplit(settings.MCP_PUBLIC_URL))],
    )


def build_app() -> Starlette:
    mcp = build_server()
    session_manager = StreamableHTTPSessionManager(
        app=mcp._lowlevel_server,
        json_response=False,
        stateless=False,
        security_settings=_security_settings(),
        max_request_body_size=1024 * 1024,
        session_idle_timeout=30 * 60,
        max_sessions=500,
    )
    mcp_endpoint = ProtocolVersionGuard(
        RequireAuthMiddleware(
            StreamableHTTPASGIApp(session_manager),
            required_scopes=[settings.MCP_OAUTH_SCOPE],
            resource_metadata_url=f"{settings.MCP_PUBLIC_URL}/.well-known/oauth-protected-resource/mcp",
        )
    )
    django_app = OAuthDjangoApp()
    routes = [Route("/mcp", endpoint=mcp_endpoint)]
    routes += [Route(path, endpoint=django_app) for path in WELL_KNOWN]
    routes.append(Route("/oauth/{rest:path}", endpoint=django_app))

    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(AuthenticationMiddleware, backend=BearerAuthBackend(DjangoTokenVerifier())),
            Middleware(AuthContextMiddleware),
        ],
        exception_handlers={404: not_found, 405: not_found},
        lifespan=lambda _app: session_manager.run(),
    )
    app.router.redirect_slashes = False
    app.state.mcp = mcp
    app.state.session_manager = session_manager
    return app
