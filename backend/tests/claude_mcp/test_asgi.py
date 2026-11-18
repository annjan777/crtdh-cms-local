"""The MCP hostname's ASGI app: what exists, who gets in, what leaks."""

import pytest
from asgiref.sync import sync_to_async

from .conftest import http_client, issue_token, mcp_client, running

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio, pytest.mark.security]

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.mark.parametrize("path", [
    "/", "/admin/", "/admin/login/", "/api/v1/hero-slides/", "/api/v1/auth/me/", "/api/v1/cms/claude-access/revoke/",
    "/media/x.jpg", "/static/x.css", "/oauth/applications/", "/oauth/introspect/", "/oauth/authorized_tokens/",
    "/.well-known/openid-configuration", "/.well-known/jwks.json", "/mcp/", "/mcp/extra", "/oauth/../api/v1/",
    "/sse", "/messages/",
])
async def test_only_mcp_and_oauth_paths_exist(asgi_app, path):
    async with running(asgi_app), http_client(asgi_app) as hc:
        for method in ("GET", "POST"):
            resp = await hc.request(method, path)
            assert resp.status_code == 404, (method, path, resp.status_code)


async def test_metadata_served_over_http(asgi_app):
    async with running(asgi_app), http_client(asgi_app) as hc:
        as_meta = (await hc.get("/.well-known/oauth-authorization-server")).json()
        assert as_meta["issuer"] == "http://localhost:8400"
        assert as_meta["authorization_endpoint"] == "https://cms.example.org/oauth/authorize/"
        for path in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"):
            pr = (await hc.get(path)).json()
            assert pr["resource"] == "http://localhost:8400/mcp"


async def test_token_endpoint_reachable_on_mcp_host(asgi_app):
    async with running(asgi_app), http_client(asgi_app) as hc:
        resp = await hc.post("/oauth/token/", data={"grant_type": "authorization_code", "code": "nope"})
        assert resp.status_code in (400, 401)
        assert resp.headers["content-type"].startswith("application/json")


async def test_mcp_without_token_gets_401_with_resource_metadata(asgi_app):
    async with running(asgi_app), http_client(asgi_app, **MCP_HEADERS) as hc:
        resp = await hc.post("/mcp", json=INIT)
        assert resp.status_code == 401
        challenge = resp.headers["www-authenticate"]
        assert challenge.startswith("Bearer ")
        assert 'resource_metadata="http://localhost:8400/.well-known/oauth-protected-resource/mcp"' in challenge


@pytest.mark.parametrize("kind", ["garbage", "expired", "wrong_scope", "inactive_user"])
async def test_bad_tokens_are_refused(asgi_app, editor, claude_app, kind):
    @sync_to_async
    def make():
        if kind == "garbage":
            return "not-a-real-token"
        if kind == "expired":
            return issue_token(editor, claude_app, expires_in=-5)
        if kind == "wrong_scope":
            return issue_token(editor, claude_app, scope="read write")
        raw = issue_token(editor, claude_app)
        type(editor).objects.filter(pk=editor.pk).update(is_active=False)  # bypasses signals on purpose
        return raw

    raw = await make()
    async with running(asgi_app), http_client(asgi_app, raw, **MCP_HEADERS) as hc:
        assert (await hc.post("/mcp", json=INIT)).status_code == 401


async def test_unsupported_protocol_version_refused(asgi_app, token):
    async with running(asgi_app), http_client(asgi_app, token, **MCP_HEADERS) as hc:
        resp = await hc.post("/mcp", json=INIT, headers={"MCP-Protocol-Version": "2026-07-28"})
        assert resp.status_code == 400
        assert "2025-11-25" in resp.json()["error"]["message"]


async def test_wrong_host_header_refused(asgi_app, token):
    async with running(asgi_app), http_client(asgi_app, token, **MCP_HEADERS) as hc:
        resp = await hc.post("/mcp", json=INIT, headers={"Host": "evil.example.com"})
        assert resp.status_code == 421


async def test_negotiates_pinned_version(asgi_app, token):
    async with mcp_client(asgi_app, token) as client:
        assert client.protocol_version in ("2025-06-18", "2025-11-25")
        assert client.server_info.name == "crtdh-cms"


async def test_deactivation_cuts_an_open_session(asgi_app, editor, token):
    async with mcp_client(asgi_app, token) as client:
        assert not (await client.call_tool("list_pending_changes", {})).is_error

        @sync_to_async
        def deactivate():
            editor.is_active = False
            editor.save()
        await deactivate()
        with pytest.raises(Exception):
            await client.call_tool("list_pending_changes", {})


async def test_role_removed_mid_session_gives_forbidden_role(asgi_app, editor, token):
    async with mcp_client(asgi_app, token) as client:
        assert not (await client.call_tool("list_pending_changes", {})).is_error
        await sync_to_async(editor.groups.clear)()
        res = await client.call_tool("list_pending_changes", {})
        assert res.is_error and res.structured_content["code"] == "CMS_FORBIDDEN_ROLE"


async def test_revoke_from_cms_cuts_an_open_session(asgi_app, editor, token):
    from apps.oauth.revoke import revoke_all_for_user

    async with mcp_client(asgi_app, token) as client:
        assert not (await client.call_tool("list_pending_changes", {})).is_error
        await sync_to_async(revoke_all_for_user)(editor, reason="test")
        with pytest.raises(Exception):
            await client.call_tool("list_pending_changes", {})


async def test_internal_errors_leak_nothing(asgi_app, token, monkeypatch):
    from mcp_server import cms

    def boom(actor, query, limit=10):
        raise RuntimeError("db password=hunter2 at /srv/secret/path Traceback")
    monkeypatch.setattr(cms, "find_content", boom)
    async with mcp_client(asgi_app, token) as client:
        res = await client.call_tool("find_content", {"query": "x"})
    assert res.is_error
    body = res.structured_content
    assert body["code"] == "CMS_INTERNAL" and body["retryable"] is True and len(body["request_id"]) == 16
    blob = repr(body) + res.content[0].text
    for secret in ("hunter2", "/srv/secret", "Traceback", "RuntimeError", token):
        assert secret not in blob
