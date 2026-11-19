"""Probe: does the admin page editor still render its preview iframe when the admin is served with the
production gateway's headers (deploy/nginx/templates/gateway.conf.template, `location /`)?
Playwright adds exactly those headers to every admin HTML response (preprod's static host sends none).
Usage: set -a; . .preprod/env; set +a; python tests/tools/wave2/gateway_frame_probe.py [user]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
from helpers import totp_now  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

import os  # noqa: E402

CMS = "https://localhost:3600"
GATEWAY_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; "
               "connect-src 'self'; frame-src https://www.youtube-nocookie.com https://www.google.com; "
               "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
HEADERS = {"content-security-policy": GATEWAY_CSP, "x-frame-options": "DENY"}


def run(user, with_headers):
    users = json.loads(Path(".preprod/users.json").read_text())
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN") or None)
        ctx = b.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        failed = []
        page.on("requestfailed", lambda r: failed.append(f"{r.url} {r.failure}"))
        page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        if with_headers:
            def add(route):
                if route.request.resource_type == "document":
                    r = route.fetch()
                    route.fulfill(response=r, headers={**r.headers, **HEADERS})
                else:
                    route.continue_()
            ctx.route("**/*", add)
        page.goto(f"{CMS}/login")
        page.get_by_label(re.compile("user ?name|email", re.I)).fill(user)
        page.get_by_label(re.compile("password", re.I)).fill(os.environ["CRTDH_TEST_PASSWORD"])
        page.get_by_role("button", name=re.compile("sign in|log in", re.I)).click()
        page.get_by_label(re.compile("code", re.I)).fill(totp_now(users[user]["totp_secret"]))
        page.get_by_role("button", name=re.compile(r"^\s*(verify|continue)", re.I)).click()
        page.wait_for_timeout(3000)
        page.goto(f"{CMS}/pages/home")
        page.wait_for_timeout(5000)
        frame = next((f for f in page.frames if f.url.endswith("/preview.html")), None)
        text = frame.evaluate("() => document.body ? document.body.innerText.length : -1") if frame else None
        url_now = page.url
        shot = f"docs/test-evidence/2026-11-19/gateway-frame-{'with' if with_headers else 'without'}-headers.png"
        page.screenshot(path=shot)
        b.close()
        return {"gateway_headers": with_headers, "preview_frame_found": bool(frame), "preview_text_len": text,
                "console_errors": errors[:8], "failed": failed[:10], "url": url_now, "screenshot": shot}


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "ada_admin"
    for h in (False, True):
        print(json.dumps(run(u, h)))
