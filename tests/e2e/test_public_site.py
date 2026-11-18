"""Public site (TEST-PLAN: Affected Pages/Routes, Edge Cases on public rendering, placeholder sweep, visual check).

Runs against the *prerendered* build served as static files (stands in for CIC).
"""
import json
import os
import re
import urllib.request
from pathlib import Path

import pytest

from conftest import ROUTES, VIEWPORTS
from helpers import axe_serious, horizontal_overflow, record_api_calls

pytestmark = pytest.mark.needs_integration
RESULTS = Path(__file__).resolve().parents[2] / "test-results"
PLACEHOLDER = re.compile(r"\b(lorem|ipsum|todo|placeholder|sample text|tbd|xxx)\b", re.I)
ALLOWED_FONTS = {f.strip().lower() for f in os.environ.get(
    "E2E_ALLOWED_FONTS", "Open Sans,Montserrat,system-ui,-apple-system,sans-serif,serif,monospace").split(",")}
SAMPLE = json.loads((Path(__file__).resolve().parents[2] / "backend/tests/fixtures/sample_snapshot.json").read_text())


def raw(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


@pytest.mark.parametrize("route", ROUTES)
def test_prerendered_html_contains_content(site, route):
    status, html = raw(site + route)
    assert status == 200
    assert re.search(r"<h1[^>]*>\s*\S", html), "no prerendered <h1>"
    assert "<main" in html
    assert "HIDDEN SLIDE" not in html, "is_published=false item leaked into HTML"


def test_team_page_lists_published_members(site):
    _, html = raw(site + "/team")
    for m in SAMPLE["collections"]["team-members"]:
        if m["is_published"]:
            assert m["name"].split(" / ")[0] in html, m["name"]


@pytest.mark.parametrize("route", ROUTES)
def test_no_cms_api_calls(page, site, route):
    calls = record_api_calls(page)
    page.goto(site + route, wait_until="networkidle")
    assert calls == [], f"public page called the CMS API: {calls}"


@pytest.mark.parametrize("route", ROUTES)
def test_content_visible_without_js(browser, site, route):
    ctx = browser.new_context(java_script_enabled=False)
    p = ctx.new_page()
    p.goto(site + route)
    assert p.locator("h1").first.is_visible()
    ctx.close()


@pytest.mark.a11y
@pytest.mark.parametrize("route", ROUTES)
def test_axe_no_serious_violations(page, site, route):
    page.goto(site + route, wait_until="networkidle")
    bad = axe_serious(page)
    assert not bad, [(v["id"], v["impact"], len(v["nodes"])) for v in bad]


@pytest.mark.a11y
@pytest.mark.parametrize("route", ROUTES)
def test_landmarks_and_skip_link(page, site, route):
    page.goto(site + route)
    for sel in ["header", "nav", "main", "footer"]:
        assert page.locator(sel).count() >= 1, sel
    page.keyboard.press("Tab")
    focused = page.evaluate("() => document.activeElement && document.activeElement.textContent")
    assert focused and re.search(r"skip", focused, re.I), "first Tab stop should be the skip link"


@pytest.mark.parametrize("vp", list(VIEWPORTS))
@pytest.mark.parametrize("route", ROUTES)
def test_no_horizontal_overflow(page, site, route, vp):
    page.set_viewport_size(dict(zip(("width", "height"), VIEWPORTS[vp])))
    page.goto(site + route, wait_until="networkidle")
    assert horizontal_overflow(page) <= 0


def test_long_and_indic_names_do_not_overflow(page, site):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(site + "/team", wait_until="networkidle")
    over = page.evaluate("""() => [...document.querySelectorAll('main *')].filter(e => e.scrollWidth > e.clientWidth + 1
        && getComputedStyle(e).overflowX === 'visible' && e.children.length === 0).map(e => e.textContent.slice(0, 60))""")
    assert not over, over


def test_designed_404(page, site):
    resp = page.goto(site + "/no-such-page-xyz")
    assert resp.status == 404
    assert page.locator("h1").first.is_visible()
    assert page.get_by_role("link", name=re.compile("home", re.I)).count() >= 1


def test_sitemap_lists_every_route(site):
    status, xml = raw(site + "/sitemap.xml")
    assert status == 200
    locs = {re.sub(r"^https?://[^/]+", "", u).rstrip("/") or "/" for u in re.findall(r"<loc>([^<]+)</loc>", xml)}
    assert set(ROUTES) <= locs, set(ROUTES) - locs


@pytest.mark.parametrize("route", ROUTES)
def test_seo_meta(site, route):
    _, html = raw(site + route)
    assert re.search(r"<title>[^<]{5,}</title>", html)
    for pat in [r'<meta[^>]+name="description"[^>]+content="[^"]{20,}"', r'<link[^>]+rel="canonical"',
                r'<meta[^>]+property="og:image"', r'<meta[^>]+property="og:title"']:
        assert re.search(pat, html), pat


@pytest.mark.parametrize("route", ROUTES)
def test_placeholder_and_broken_content_sweep(page, site, route):
    page.goto(site + route, wait_until="networkidle")
    text = page.locator("body").inner_text()
    assert not PLACEHOLDER.search(text), PLACEHOLDER.search(text).group(0)
    empty_h = page.evaluate("() => [...document.querySelectorAll('h1,h2,h3,h4')].filter(h => !h.textContent.trim()).length")
    assert empty_h == 0, "empty heading"
    imgs = page.evaluate("""() => [...document.images].map(i => ({src: i.currentSrc || i.src, ok: i.complete && i.naturalWidth > 0,
        alt: i.hasAttribute('alt'), lazy: i.loading === 'lazy'}))""")
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(800)
    imgs = page.evaluate("() => [...document.images].map(i => ({src: i.currentSrc || i.src, ok: i.complete && i.naturalWidth > 0, alt: i.hasAttribute('alt')}))")
    assert all(i["alt"] for i in imgs), [i["src"] for i in imgs if not i["alt"]]
    assert all(i["ok"] for i in imgs), [i["src"] for i in imgs if not i["ok"]]
    hrefs = page.evaluate("() => [...document.querySelectorAll('a[href^=\"/\"]')].map(a => a.getAttribute('href'))")
    internal = {h.split("#")[0].split("?")[0].rstrip("/") or "/" for h in hrefs if not h.startswith("/media/")}
    missing = [h for h in internal if h not in ROUTES and not h.endswith((".pdf", ".xml"))]
    assert not missing, f"links to pages that don't exist: {missing}"


@pytest.mark.visual
@pytest.mark.parametrize("vp", list(VIEWPORTS))
@pytest.mark.parametrize("route", ROUTES)
def test_visual_baseline_and_fonts(page, site, route, vp):
    page.set_viewport_size(dict(zip(("width", "height"), VIEWPORTS[vp])))
    page.goto(site + route, wait_until="networkidle")
    out = RESULTS / "visual" / f"{route.strip('/') or 'home'}-{vp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out), full_page=True)
    fams = page.evaluate("() => [...new Set([...document.querySelectorAll('body *')].map(e => getComputedStyle(e).fontFamily))]")
    used = {f.strip().strip('"\'').lower() for fam in fams for f in fam.split(",")[:1]}
    assert used <= ALLOWED_FONTS, f"off-system fonts: {used - ALLOWED_FONTS}"


@pytest.mark.perf
def test_home_js_budget(page, site):
    sizes = []
    page.on("response", lambda r: sizes.append(int(r.headers.get("content-length", 0) or 0))
            if r.request.resource_type == "script" else None)
    page.goto(site + "/", wait_until="networkidle")
    # transfer size proxy; the real gzip budget (150 KB) is enforced by scripts/check-bundle-size.sh in CI
    assert sum(sizes) < 600_000, sum(sizes)
