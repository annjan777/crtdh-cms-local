"""Trusted-proxy guard in front of the whole MCP ASGI app (Starlette routes don't pass
through backend-security's Django TrustedProxyMiddleware)."""

import contextlib

import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from mcp_server.proxy_guard import TrustedProxyGuard

from .conftest import MCP_URL

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio, pytest.mark.security]

GATEWAY = ("172.30.0.10", 51000)
STRANGER = ("172.30.0.99", 51000)


@pytest.fixture(autouse=True)
def proxies(settings):
    settings.TRUSTED_PROXY_IPS = ["172.30.0.10", "172.30.0.11/32"]
    settings.REQUIRE_TRUSTED_PROXY = True


def client_for(app, peer, **headers):
    return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app, client=peer),
                              base_url="http://localhost:8400", headers=headers, timeout=20)


@contextlib.asynccontextmanager
async def guarded(asgi_app):
    async with asgi_app.router.lifespan_context(asgi_app):
        yield TrustedProxyGuard(asgi_app)


@pytest.mark.parametrize("method,path", [
    ("POST", "/mcp"), ("GET", "/.well-known/oauth-authorization-server"),
    ("GET", "/.well-known/oauth-protected-resource/mcp"), ("POST", "/oauth/token/"), ("GET", "/nope"),
])
async def test_direct_peers_are_refused(asgi_app, method, path):
    async with guarded(asgi_app) as app, client_for(app, STRANGER) as hc:
        resp = await hc.request(method, path)
        assert resp.status_code == 403 and resp.content == b""


async def test_forged_forwarding_headers_do_not_make_a_peer_trusted(asgi_app):
    async with guarded(asgi_app) as app, client_for(app, STRANGER, **{"X-Forwarded-For": "172.30.0.10",
                                                                     "CF-Connecting-IP": "160.79.104.1"}) as hc:
        assert (await hc.get("/.well-known/oauth-authorization-server")).status_code == 403


async def test_gateway_peer_gets_through(asgi_app, token):
    async with guarded(asgi_app) as app:
        async with client_for(app, GATEWAY) as hc:
            assert (await hc.get("/.well-known/oauth-authorization-server")).status_code == 200
        async with client_for(app, GATEWAY, Authorization=f"Bearer {token}") as hc:
            async with Client(streamable_http_client(MCP_URL, http_client=hc), mode="legacy") as client:
                res = await client.call_tool("list_pending_changes", {})
                assert not res.is_error


async def _seen_headers(peer, settings, require):
    settings.REQUIRE_TRUSTED_PROXY = require
    seen = {}

    async def inner(scope, receive, send):
        seen.update({k.decode(): v.decode() for k, v in scope["headers"]})
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    forged = {"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "evil",
              "X-Real-IP": "1.2.3.4", "Forwarded": "for=1.2.3.4", "CF-Connecting-IP": "1.2.3.4", "X-Other": "kept"}
    async with client_for(TrustedProxyGuard(inner), peer, **forged) as hc:
        assert (await hc.get("/anything")).status_code == 204
    return seen


async def test_untrusted_peer_loses_forwarding_headers_when_not_required(settings):
    seen = await _seen_headers(STRANGER, settings, require=False)
    for h in ("x-forwarded-for", "x-forwarded-proto", "x-forwarded-host", "x-real-ip", "forwarded", "cf-connecting-ip"):
        assert h not in seen
    assert seen["x-other"] == "kept"


async def test_trusted_peer_keeps_forwarding_headers(settings):
    seen = await _seen_headers(GATEWAY, settings, require=True)
    assert seen["cf-connecting-ip"] == "1.2.3.4" and seen["x-forwarded-proto"] == "https"


async def test_lifespan_passes_through(settings):
    events = []

    async def inner(scope, receive, send):
        events.append(scope["type"])

    await TrustedProxyGuard(inner)({"type": "lifespan"}, None, None)
    assert events == ["lifespan"]


def test_asgi_entry_point_is_guarded():
    from mcp_server import asgi

    assert isinstance(asgi.app, TrustedProxyGuard)
