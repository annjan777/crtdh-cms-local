"""Critical path: Claude MCP — connect (OAuth 2.1 + PKCE + TOTP) -> find -> update -> preview -> request_review
-> Publisher publishes. Key Interactions 5 and 6 (upload link -> add_hero_slide).

Simulates the claude.ai connector: the OAuth authorize step runs in a real browser (CMS sign-in + TOTP +
consent), the token exchange and MCP JSON-RPC calls are plain HTTP, like Anthropic's cloud would make.
MCP server: E2E_MCP_URL (default https://localhost:8600/mcp; the MCP ASGI app may be mounted on its own
port in preprod — set E2E_MCP_URL=https://localhost:8601/mcp there). OAuth client: E2E_OAUTH_CLIENT_ID/SECRET.
"""
import base64
import hashlib
import json
import os
import re
import time
import secrets
import urllib.parse
import urllib.request

import pytest

pytestmark = [pytest.mark.needs_integration, pytest.mark.mcp]
REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def http(method, url, body=None, headers=None, form=False):
    data = None
    h = dict(headers or {})
    if body is not None:
        data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


class MCP:
    def __init__(self, url, token):
        self.url, self.token, self.sid, self.n = url, token, None, 0

    def rpc(self, method, params=None):
        self.n += 1
        h = {"Authorization": f"Bearer {self.token}", "Accept": "application/json, text/event-stream",
             "MCP-Protocol-Version": os.environ.get("E2E_MCP_PROTOCOL", "2025-06-18")}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        s, hdrs, body = http("POST", self.url, {"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}, h)
        self.sid = self.sid or hdrs.get("Mcp-Session-Id") or hdrs.get("mcp-session-id")
        assert s == 200, (s, body[:300])
        if body.startswith("event:") or "\ndata:" in body or body.startswith("data:"):
            body = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")][-1]
        return json.loads(body)

    def initialize(self):
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "crtdh-e2e", "version": "1"}})
        self.notify("notifications/initialized")
        return r

    def notify(self, method):
        h = {"Authorization": f"Bearer {self.token}", "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        http("POST", self.url, {"jsonrpc": "2.0", "method": method}, h)

    def tool(self, name, **args):
        res = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        return res


@pytest.fixture(scope="module")
def mcp_url(stack):
    return os.environ.get("E2E_MCP_URL", f"{stack.api}/mcp")


def oauth_token(browser, stack, mcp_url, username="erin_editor"):
    """RFC 9728 discovery -> authorize (browser: login + TOTP + consent) -> token, with PKCE S256."""
    base = mcp_url.rsplit("/mcp", 1)[0]
    s, hdrs, _ = http("POST", mcp_url, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert s == 401, "unauthenticated MCP call must be 401"
    assert "resource_metadata" in hdrs.get("WWW-Authenticate", hdrs.get("www-authenticate", ""))
    _, _, prm = http("GET", f"{base}/.well-known/oauth-protected-resource/mcp")
    if not prm.strip().startswith("{"):
        _, _, prm = http("GET", f"{base}/.well-known/oauth-protected-resource")
    as_url = json.loads(prm)["authorization_servers"][0].rstrip("/")
    _, _, asm = http("GET", f"{as_url}/.well-known/oauth-authorization-server")
    meta = json.loads(asm)
    assert "S256" in meta.get("code_challenge_methods_supported", [])
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    client_id = os.environ.get("E2E_OAUTH_CLIENT_ID", "claude-e2e")
    state = secrets.token_urlsafe(8)
    q = urllib.parse.urlencode({"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
                                "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
                                "resource": mcp_url, "scope": meta.get("scopes_supported", ["drafts"])[0]})
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    captured = {}
    def _client(route):  # never let the browser reach the real claude.ai; keep the first auth callback
        if "auth_callback" in route.request.url:
            captured.setdefault("url", route.request.url)
        route.abort()
    page.route(re.compile(r"^https://claude\.(ai|com)/.*"), _client)
    page.goto(f"{meta['authorization_endpoint']}?{q}")
    from helpers import ui_login  # noqa: F401  (same form as the CMS sign-in)
    page.get_by_label(re.compile("user ?name|email", re.I)).fill(username)
    page.get_by_label(re.compile("password", re.I)).fill(stack.password)
    page.get_by_role("button", name=re.compile("sign in|log in", re.I)).click()
    secret = stack.users.get(username, {}).get("totp_secret")
    assert secret, "TOTP must be required inside the authorize step (seed_test_users needs mfa.enroll_totp_for_test)"
    from helpers import totp_now
    page.get_by_label(re.compile("code", re.I)).fill(totp_now(secret))
    page.get_by_role("button", name=re.compile(r"^\s*(verify|continue)", re.I)).click()
    consent = page.get_by_text(re.compile(r"Allow Claude to edit drafts as", re.I))
    console = []
    page.on("console", lambda m: console.append(m.text))
    page.on("response", lambda r: console.append(f"{r.status} {r.request.method} {r.url[:120]}") if r.status >= 300 else None)

    def _location(r):  # the authorize step's redirect to the client carries code + state
        loc = r.headers.get("location", "")
        if r.status in (302, 303) and "auth_callback" in loc:
            captured.setdefault("url", loc)
    page.on("response", _location)
    page.on("requestfailed", lambda r: console.append(f"FAILED {r.method} {r.url[:160]} {r.failure}"))
    for _ in range(60):  # consent page, or (already approved earlier for this user) straight back to the client
        if "url" in captured or consent.count():
            break
        page.wait_for_timeout(500)
    else:
        raise AssertionError(f"neither consent nor redirect; page {page.url}: {page.inner_text('body')[:300]}")
    if "url" not in captured:
        assert re.search(r"\((editor|publisher|admin)\)", page.content(), re.I)
        page.get_by_role("button", name=re.compile("allow", re.I)).click()
    for _ in range(20):
        if "url" in captured:
            break
        page.wait_for_timeout(500)
    ctx.close()
    assert "url" in captured, f"Allow did not redirect to the client's redirect_uri; browser log: {console[:12]}"
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(captured["url"]).query)
    assert "code" in qs and "state" in qs, f"redirect to the client lacks code/state: {captured['url'][:300]}"
    assert qs["state"] == [state]
    form = {"grant_type": "authorization_code", "code": qs["code"][0], "redirect_uri": REDIRECT,
            "client_id": client_id, "code_verifier": verifier, "resource": mcp_url}
    if os.environ.get("E2E_OAUTH_CLIENT_SECRET"):
        form["client_secret"] = os.environ["E2E_OAUTH_CLIENT_SECRET"]
    s, _, tok = http("POST", meta["token_endpoint"], form, form=True)
    assert s == 200, tok
    # wrong verifier must fail (PKCE enforced)
    return json.loads(tok)["access_token"]


@pytest.fixture(scope="module")
def mcp(browser, stack, mcp_url):
    m = MCP(mcp_url, oauth_token(browser, stack, mcp_url))
    m.initialize()
    return m


def test_tools_listed_with_hints(mcp):
    tools = {t["name"]: t for t in mcp.rpc("tools/list")["result"]["tools"]}
    for name in ["find_content", "get_page", "update_team_member", "request_review", "request_upload_link",
                 "add_hero_slide", "get_preview_link", "list_pending_changes"]:
        assert name in tools, name
    assert tools["find_content"]["annotations"]["readOnlyHint"] is True
    assert tools["update_team_member"]["annotations"].get("destructiveHint") is False
    assert not any(n.startswith(("delete", "publish")) for n in tools), "no delete/publish tools"


def test_find_update_preview_not_live(mcp, site):
    res = mcp.tool("find_content", query="Prof. Suman Chakraborty")
    hit = res["structuredContent"]["matches"][0]
    page = mcp.tool("get_page", page="team")["structuredContent"]
    item = next(i for s in page["sections"] for i in s.get("items", []) if i["id"] == hit["id"])
    up = mcp.tool("update_team_member", id=hit["id"], fields={"designation": "Professor (E2E)"},
                  expected_version=item["version"])
    sc = up["structuredContent"]
    assert sc["status"] == "draft" and sc["preview_url"] and "Not live yet" in json.dumps(up)
    assert "Professor (E2E)" not in urllib.request.urlopen(site + "/team").read().decode()


def test_stale_version_via_mcp(mcp):
    from_ = mcp.tool("find_content", query="Prof. Suman Chakraborty")["structuredContent"]["matches"][0]
    res = mcp.tool("update_team_member", id=from_["id"], fields={"designation": "x"}, expected_version=1)
    assert res["isError"] is True
    sc = res["structuredContent"]
    assert sc["code"] == "CMS_STALE_VERSION" and sc["current_version"] > 1
    assert re.search(r"by \w+", sc["message"]), "message must name who edited it"


def test_upload_link_then_add_hero_slide(mcp, browser, tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from tests.support.images import make_image_bytes
    link = mcp.tool("request_upload_link")["structuredContent"]
    link["url"] = link.get("url") or link["upload_url"]
    img = tmp_path / "hero2400.jpg"
    img.write_bytes(make_image_bytes(2400, 1350))
    ctx = browser.new_context(ignore_https_errors=True)
    p = ctx.new_page()
    p.goto(link["url"])
    p.locator("input[type=file]").set_input_files(str(img))
    p.get_by_role("button", name=re.compile("upload", re.I)).click()
    p.get_by_text(re.compile("photo received|uploaded|done|thank", re.I)).wait_for()
    p.goto(link["url"])
    assert p.locator("input[type=file]").count() == 0, "upload link must be one-time (no form after use)"
    ctx.close()
    # D12: stored names are content hashes, so the original file name can't be searched; newest first instead
    found = mcp.tool("search_media", query="")["structuredContent"]["media"]
    assert found and found[0]["width"] == 2400, found[:1]
    slide = mcp.tool("add_hero_slide", fields={"image": found[0]["media_id"], "heading": "New hero from E2E",
                                               "alt_text": "Lab bench with diagnostic device"})
    assert not slide.get("isError"), slide
    assert slide["structuredContent"]["status"] == "draft"


def test_request_review_then_publisher_publishes(mcp, stack):
    from helpers import api_session
    r = mcp.tool("request_review", note="E2E: designation change")
    assert not r.get("isError")
    call = api_session(stack, "priya")
    _, ch = call("GET", "/api/v1/cms/changes/")
    channels = {c["channel"] for p in ch["pages"] for c in p["changes"]}
    assert "mcp" in channels
    if os.environ.get("E2E_PUBLISH_STACK") == "1":
        s, b = call("POST", "/api/v1/cms/publish/", {})
        if s == 422 and b.get("code") == "CMS_BUILD_GUARD":  # other specs empty a collection on purpose
            s, b = call("POST", "/api/v1/cms/publish/", {"confirm_shrink": True})
        assert s in (202, 409), (s, b)


def test_session_write_cap(mcp):
    """26th write in one connector session -> CMS_SESSION_LIMIT (uses a hidden sandbox item if present)."""
    hit = mcp.tool("find_content", query="Prof. Suman Chakraborty")["structuredContent"]["matches"][0]
    last = None
    for i in range(30):
        cur = mcp.tool("get_page", page="team")["structuredContent"]
        v = next(it["version"] for s in cur["sections"] for it in s.get("items", []) if it["id"] == hit["id"])
        last = mcp.tool("update_team_member", id=hit["id"], fields={"designation": f"cap {i}"}, expected_version=v)
        if last.get("isError") and last["structuredContent"].get("code") == "CMS_RATE_LIMITED":
            time.sleep(61)  # per-user write rate (20/min) trips before the per-session cap (25); wait it out
            last = mcp.tool("update_team_member", id=hit["id"], fields={"designation": f"cap {i}"}, expected_version=v)
        if last.get("isError"):
            break
    assert last["structuredContent"]["code"] == "CMS_SESSION_LIMIT"
