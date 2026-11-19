"""axe-core on every public page and every admin screen at 375 and 1280 px (serious + critical counted).
    set -a; . .preprod/env; set +a; python tests/tools/wave2/a11y.py --site URL --admin URL --out results.json"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
from axe_playwright_python.sync_playwright import Axe  # noqa: E402
from helpers import totp_now  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PUBLIC = ["/", "/about", "/team", "/innovations", "/facilities", "/services", "/product", "/enterprises",
          "/social-impact", "/covid-19", "/media", "/contact", "/no-such-page"]
ADMIN = ["/pages/home", "/pages/about", "/pages/team", "/pages/media", "/pages/contact", "/review", "/history",
         "/users", "/messages", "/shot-list"]
WIDTHS = [375, 1280]


def scan(page, label, rows):
    res = Axe().run(page).response
    bad = [v for v in res["violations"] if v.get("impact") in ("serious", "critical")]
    rows.append({"screen": label, "width": page.viewport_size["width"], "serious_critical": len(bad),
                 "moderate_minor": len(res["violations"]) - len(bad),
                 "violations": [{"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]),
                                 "example": v["nodes"][0]["target"] if v["nodes"] else None} for v in res["violations"]]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site")
    ap.add_argument("--admin")
    ap.add_argument("--user", default="ada_admin")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN") or None)
        if a.site:
            ctx = b.new_context(ignore_https_errors=True)
            page = ctx.new_page()
            for w in WIDTHS:
                page.set_viewport_size({"width": w, "height": 900})
                for r in PUBLIC:
                    page.goto(a.site + r, wait_until="networkidle")
                    scan(page, f"site {r}", rows)
            ctx.close()
        if a.admin:
            users = json.loads(Path(".preprod/users.json").read_text())
            ctx = b.new_context(ignore_https_errors=True)
            page = ctx.new_page()
            for w in WIDTHS:
                page.set_viewport_size({"width": w, "height": 900})
                page.goto(a.admin + "/login", wait_until="networkidle")
                scan(page, "admin /login", rows)
            page.get_by_label(re.compile("user ?name", re.I)).fill(a.user)
            page.get_by_label(re.compile("password", re.I)).fill(os.environ["CRTDH_TEST_PASSWORD"])
            page.get_by_role("button", name=re.compile("^sign in", re.I)).click()
            page.get_by_label(re.compile("^code", re.I)).wait_for()
            for w in WIDTHS:
                page.set_viewport_size({"width": w, "height": 900})
                scan(page, "admin MFA screen", rows)
            page.get_by_label(re.compile("^code", re.I)).fill(totp_now(users[a.user]["totp_secret"]))
            page.get_by_role("button", name=re.compile(r"^\s*verify", re.I)).click()
            page.wait_for_timeout(3000)
            for w in WIDTHS:
                page.set_viewport_size({"width": w, "height": 900})
                for r in ADMIN:
                    page.goto(a.admin + r, wait_until="networkidle")
                    page.wait_for_timeout(1500)
                    scan(page, f"admin {r}", rows)
            ctx.close()
        b.close()
    for r in rows:
        print(f"{r['serious_critical']:3} serious/critical {r['moderate_minor']:3} other  {r['width']:5}  {r['screen']}  "
              + ", ".join(f"{v['id']}({v['impact']},{v['nodes']})" for v in r["violations"]))
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)
    return 1 if any(r["serious_critical"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
