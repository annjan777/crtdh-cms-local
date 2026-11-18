"""Security header / cookie / CSP checker for a running CRTDH stack (preprod, staging, production).

    python tests/tools/check_headers.py --cms https://localhost:8600 --site https://localhost:3601 \
        --ca .preprod/tls/cert.pem [--user priya --password-env CRTDH_TEST_PASSWORD]

Checks (FAIL = must fix before go-live, WARN = review):
  every response: HSTS >= 1 year (+includeSubDomains), nosniff, Referrer-Policy, framing blocked
    (X-Frame-Options DENY/SAMEORIGIN or CSP frame-ancestors), no Server/X-Powered-By version leak;
  CMS: CSP present, script-src without 'unsafe-inline'/'unsafe-eval'/*, object-src 'none', base-uri set,
    frame-ancestors set; API JSON is Cache-Control no-store when authenticated;
  cookies (from GET /api/v1/auth/csrf/ and, with --user, a password sign-in): Secure, HttpOnly on session
    and csrf cookies, SameSite Lax/Strict, __Host- prefix rules (Secure, Path=/, no Domain);
  public site: CSP (meta or header) without 'unsafe-eval', no inline event handlers in HTML.
Exit 1 if any FAIL. The public site on the CIC host gets its headers from the generated .htaccess: check that
file offline with --htaccess build/client/.htaccess, and run --site against the real host once after the first
upload (whether CIC's Apache honours mod_headers cannot be proven in the sandbox; the local static host sends none).
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from http.cookies import SimpleCookie

RESULTS = []


def res(level, where, msg):
    RESULTS.append((level, where, msg))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(opener, url, method="GET", body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        r = opener.open(req, timeout=15)
    except urllib.error.HTTPError as e:
        r = e
    return r.status if hasattr(r, "status") else r.code, r.headers, r.read()


def csp_directives(csp):
    out = {}
    for part in (csp or "").split(";"):
        bits = part.strip().split()
        if bits:
            out[bits[0].lower()] = bits[1:]
    return out


def common_headers(where, h):
    hsts = h.get("Strict-Transport-Security", "")
    m = re.search(r"max-age=(\d+)", hsts)
    if not m or int(m.group(1)) < 31536000:
        res("FAIL", where, f"HSTS missing or < 1 year: {hsts!r}")
    elif "includesubdomains" not in hsts.lower():
        res("WARN", where, "HSTS without includeSubDomains")
    if h.get("X-Content-Type-Options", "").lower() != "nosniff":
        res("FAIL", where, "X-Content-Type-Options: nosniff missing")
    if not h.get("Referrer-Policy"):
        res("WARN", where, "Referrer-Policy missing")
    xfo = h.get("X-Frame-Options", "").upper()
    fa = csp_directives(h.get("Content-Security-Policy")).get("frame-ancestors")
    if xfo not in ("DENY", "SAMEORIGIN") and not fa:
        res("FAIL", where, "framing not blocked (no X-Frame-Options and no CSP frame-ancestors)")
    for k in ("Server", "X-Powered-By"):
        if re.search(r"\d", h.get(k, "")):
            res("WARN", where, f"{k} leaks a version: {h.get(k)!r}")


def check_csp(where, csp, strict=True):
    if not csp:
        res("FAIL", where, "Content-Security-Policy missing")
        return
    d = csp_directives(csp)
    script = d.get("script-src", d.get("default-src", []))
    for bad in ("'unsafe-eval'", "*", "data:"):
        if bad in script:
            res("FAIL", where, f"CSP script-src allows {bad}")
    if "'unsafe-inline'" in script and not any(s.startswith(("'nonce-", "'sha256-")) for s in script):
        res("FAIL" if strict else "WARN", where, "CSP script-src allows 'unsafe-inline'")
    if d.get("object-src") != ["'none'"] and d.get("default-src") != ["'none'"]:
        res("WARN", where, "CSP object-src is not 'none'")
    if "base-uri" not in d:
        res("WARN", where, "CSP base-uri not set")
    if strict and "frame-ancestors" not in d:
        res("WARN", where, "CSP frame-ancestors not set")


def check_cookies(where, headers):
    raw = headers.get_all("Set-Cookie") or []
    for line in raw:
        name = line.split("=", 1)[0].strip()
        attrs = [a.strip().lower() for a in line.split(";")[1:]]
        keys = {a.split("=", 1)[0] for a in attrs}
        val = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else "") for a in attrs}
        tag = f"{where} cookie {name}"
        if "secure" not in keys:
            res("FAIL", tag, "missing Secure")
        sensitive = re.search(r"session|csrf", name, re.I)
        if sensitive and "httponly" not in keys:
            res("FAIL", tag, "missing HttpOnly")
        if val.get("samesite") not in ("lax", "strict"):
            res("FAIL" if sensitive else "WARN", tag, f"SameSite is {val.get('samesite')!r}, want Lax/Strict")
        if name.startswith("__Host-") and (val.get("path") != "/" or "domain" in keys):
            res("FAIL", tag, "__Host- cookie needs Path=/ and no Domain")
        if sensitive and not name.startswith(("__Host-", "__Secure-")):
            res("WARN", tag, "no __Host- prefix (fine in DEBUG dev only)")
        res("INFO", tag, line.split(";", 1)[1].strip() if ";" in line else "(no attributes)")
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cms", help="CMS/API origin, e.g. https://cms.example")
    ap.add_argument("--admin", help="admin SPA origin (if separate from --cms)")
    ap.add_argument("--site", help="public site origin")
    ap.add_argument("--ca", help="CA bundle for a self-signed rehearsal cert")
    ap.add_argument("--user", help="sign in as this user to check the session cookie")
    ap.add_argument("--password-env", default="CRTDH_TEST_PASSWORD")
    ap.add_argument("--htaccess", help="check the headers a built site's .htaccess will send on Apache (CIC host)")
    ap.add_argument("--json", help="write results here")
    a = ap.parse_args()
    ctx = ssl.create_default_context(cafile=a.ca) if a.ca else ssl.create_default_context()
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ctx))

    if a.cms:
        cms = a.cms.rstrip("/")
        for path in ("/api/v1/auth/csrf/", "/api/v1/auth/me/", "/api/v1/hero-slides/"):
            s, h, _ = fetch(opener, cms + path)
            common_headers(f"CMS {path}", h)
            check_csp(f"CMS {path}", h.get("Content-Security-Policy"))
            if path == "/api/v1/hero-slides/" and s == 200:
                res("FAIL", f"CMS {path}", "anonymous read of draft content allowed")
        s, h, body = fetch(opener, cms + "/api/v1/auth/csrf/")
        check_cookies("CMS csrf", h)
        if s == 200 and a.user and os.environ.get(a.password_env):
            token = json.loads(body or b"{}").get("csrfToken", "")
            jar = SimpleCookie()
            for line in h.get_all("Set-Cookie") or []:
                jar.load(line)
            cookie = "; ".join(f"{k}={v.value}" for k, v in jar.items())
            payload = json.dumps({"username": a.user, "password": os.environ[a.password_env]}).encode()
            s, h, body = fetch(opener, cms + "/api/v1/auth/login/", "POST", payload, {
                "Content-Type": "application/json", "X-CSRFToken": token, "Cookie": cookie, "Referer": cms + "/",
                "Origin": cms})
            if s != 200:
                res("WARN", "CMS login", f"sign-in returned {s}; session cookie not checked")
            check_cookies("CMS login", h)
            cc = h.get("Cache-Control", "")
            if "no-store" not in cc and "private" not in cc:
                res("WARN", "CMS login", f"authenticated response Cache-Control {cc!r} (want no-store)")
    if a.admin:
        s, h, body = fetch(opener, a.admin.rstrip("/") + "/")
        common_headers("admin /", h)
        check_csp("admin /", h.get("Content-Security-Policy"))
    if a.site:
        site = a.site.rstrip("/")
        for path in ("/", "/contact", "/team", "/does-not-exist"):
            s, h, body = fetch(opener, site + path)
            where = f"site {path}"
            if path == "/does-not-exist" and s != 404:
                res("FAIL", where, f"unknown path returned {s}, want 404")
            common_headers(where, h)
            html = body.decode("utf-8", "replace")
            meta = re.search(r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]+content=["\']([^"\']+)', html, re.I)
            check_csp(where, h.get("Content-Security-Policy") or (meta.group(1) if meta else ""), strict=False)
            if re.search(r"<[^>]+\son(click|load|error|mouseover)\s*=", html, re.I):
                res("WARN", where, "inline event handler attribute in HTML (blocked by a strict CSP)")

    if a.htaccess:
        from email.message import Message
        h = Message()
        for m in re.finditer(r'^\s*Header\s+(?:always\s+)?set\s+([\w-]+)\s+"([^"]*)"\s*$',
                             open(a.htaccess).read(), re.M):
            if m.group(1).lower() != "cache-control":
                h[m.group(1)] = m.group(2)
        common_headers(".htaccess", h)
        check_csp(".htaccess", h.get("Content-Security-Policy"), strict=False)

    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for level, where, msg in sorted(RESULTS, key=lambda r: order[r[0]]):
        print(f"{level:4} {where}: {msg}")
    fails = sum(1 for r in RESULTS if r[0] == "FAIL")
    print(f"\n{fails} FAIL, {sum(1 for r in RESULTS if r[0] == 'WARN')} WARN")
    if a.json:
        with open(a.json, "w") as f:
            json.dump([dict(zip(("level", "where", "message"), r)) for r in RESULTS], f, indent=2)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
