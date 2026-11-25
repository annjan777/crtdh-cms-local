"""Preprod smoke: edit -> publish -> the 'live' folder on the fake CIC host changed. Plus header checks.

  python tests/tools/preprod_smoke.py --state .preprod
Exit 0 = pass. Prints one line per check.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "e2e"))
from helpers import api_session  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""), flush=True)
    if not ok:
        FAILS.append(name)


def _trust(state):
    import ssl
    ca = state / "tls" / "cert.pem"
    if ca.exists():
        os.environ["E2E_CA_FILE"] = str(ca)
        urllib.request.install_opener(urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(ca)))))


class S:  # minimal Stack stand-in for api_session
    def __init__(self, state):
        env = dict(l.split("=", 1) for l in (state / "env").read_text().splitlines() if "=" in l and not l.startswith("#"))
        self.api = "https://localhost:8600"
        self.admin = "https://localhost:3600"
        self.password = env["CRTDH_TEST_PASSWORD"]
        self.users = json.loads((state / "users.json").read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=".preprod")
    ap.add_argument("--site", default="https://localhost:3601")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    state = Path(a.state)
    _trust(state)
    st = S(state)

    # 1. production posture
    try:
        urllib.request.urlopen(st.api + "/api/v1/hero-slides/", timeout=5)
        check("anonymous content read refused", False, "got 200")
    except urllib.error.HTTPError as e:
        check("anonymous content read refused", e.code == 401, str(e.code))
    r = urllib.request.urlopen(st.api + "/api/v1/auth/csrf/", timeout=5)
    h = {k.lower(): v for k, v in r.headers.items()}
    check("CSP header on CMS", "content-security-policy" in h)
    check("nosniff on CMS", h.get("x-content-type-options") == "nosniff")

    # 2. edit as publisher
    call = api_session(st, "priya")
    s, me = call("GET", "/api/v1/auth/me/")
    check("publisher signs in (password + TOTP)", s == 200 and "publisher" in (me or {}).get("roles", []), f"{s} {me}")
    s, slides = call("GET", "/api/v1/hero-slides/")
    rows = slides.get("results", slides) if isinstance(slides, dict) else slides
    if s != 200 or not isinstance(rows, list):
        check("list hero slides", False, f"{s} {str(slides)[:200]}")
        print("\nSMOKE FAILED: " + ", ".join(FAILS))
        return 1
    slide = next(r for r in rows if r.get("is_published"))
    marker = f"Preprod smoke {int(time.time())}"
    s, body = call("PATCH", f"/api/v1/hero-slides/{slide['id']}/", {"heading": marker, "expected_version": slide["version"]})
    check("draft edit saved", s == 200, f"{s} {body}")
    _, live = (lambda: (None, urllib.request.urlopen(a.site + "/").read().decode()))()
    check("draft not live before publish", marker not in live)
    s, ch = call("GET", "/api/v1/cms/changes/")
    check("review screen lists the change", s == 200 and marker in json.dumps(ch), str(s))

    # 3. publish and wait
    s, pub = call("POST", "/api/v1/cms/publish/", {"confirm_shrink": True})
    check("publish queued", s == 202, f"{s} {pub}")
    seen, end, stt = [], time.time() + a.timeout, {}
    while s == 202 and time.time() < end:
        _, stt = call("GET", f"/api/v1/cms/publish/{pub['publish_id']}/")
        if not seen or seen[-1] != stt.get("status"):
            seen.append(stt.get("status"))
            print(f"     status: {stt.get('status')} {stt.get('step') or ''} {stt.get('message') or ''}", flush=True)
        if stt.get("status") in ("live", "failed"):
            break
        time.sleep(2)
    check("publish reached live", stt.get("status") == "live", f"states {seen}: {stt.get('message')}")
    html = urllib.request.urlopen(a.site + "/").read().decode()
    check("live folder serves the change", marker in html)
    m = re.search(r'<meta name="crtdh-build" content="([^"]+)"', html)
    check("live page carries the build marker", bool(m))
    print(f"\n{'SMOKE PASSED' if not FAILS else 'SMOKE FAILED: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
