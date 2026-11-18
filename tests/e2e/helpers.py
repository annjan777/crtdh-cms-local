"""UI helpers shared by E2E specs. Selector contract (admin lane): see docs/testing.md §Selectors."""
import re

API_PATTERN = re.compile(r"/api/v1/(?!contact/)")


def ui_login(page, cms, username, password, totp_secret=None):
    page.goto(f"{cms}/login")
    page.get_by_label(re.compile("user ?name|email", re.I)).fill(username)
    page.get_by_label(re.compile("password", re.I)).fill(password)
    page.get_by_role("button", name=re.compile("sign in|log in", re.I)).click()
    if totp_secret:
        import pyotp
        page.get_by_label(re.compile("code", re.I)).fill(pyotp.TOTP(totp_secret).now())
        page.get_by_role("button", name=re.compile("verify|continue|sign in", re.I)).click()
    page.wait_for_url(re.compile(r"/(pages|$|dashboard)"), timeout=15000)
    return page


def record_api_calls(page):
    """Collect every request the page makes to the CMS API (contact form excluded)."""
    calls = []
    page.on("request", lambda r: calls.append(r.url) if API_PATTERN.search(r.url) else None)
    return calls


def axe_serious(page):
    from axe_playwright_python.sync_playwright import Axe
    results = Axe().run(page)
    return [v for v in results.response["violations"] if v.get("impact") in ("serious", "critical")]


def horizontal_overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")


def api_session(stack, username):
    """requests-like session logged into the CMS API via the contract endpoints (no UI)."""
    import json
    import urllib.request
    from http.cookiejar import CookieJar

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(method, path, body=None):
        csrf = next((c.value for c in jar if c.name == "csrftoken"), "")
        req = urllib.request.Request(stack.api + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "X-CSRFToken": csrf,
                                              "Referer": stack.admin + "/"})
        try:
            with opener.open(req, timeout=30) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw.decode(errors="replace")

    call("GET", "/api/v1/auth/csrf/")
    status, body = call("POST", "/api/v1/auth/login/", {"username": username, "password": stack.password})
    secret = stack.users.get(username, {}).get("totp_secret")
    if status == 200 and isinstance(body, dict) and body.get("mfa_required") and secret:
        import pyotp
        call("POST", "/api/v1/auth/mfa/", {"code": pyotp.TOTP(secret).now()})
    call("GET", "/api/v1/auth/csrf/")
    return call
