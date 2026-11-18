"""Capture the public-content golden for the CRITICAL prerender regression check (TEST-PLAN Critical Paths #1).

Records, per route, what a visitor sees in <main>: headings in order, visible list/card texts, and
images (alt + source basename). Run against the *pre-v3 runtime SPA* (19 Nov restored build) with the
full seed; compare later against the prerendered build with tests/e2e/test_golden_regression.py.

  python tests/tools/capture_golden.py --site http://localhost:3601 --out tests/e2e/golden/public_content.json
"""
import argparse
import json
import os
from pathlib import Path

ROUTES = ["/", "/about", "/team", "/innovations", "/facilities", "/services", "/product", "/enterprises",
          "/social-impact", "/covid-19", "/media", "/contact"]

EXTRACT_JS = r"""
() => {
  const root = document.querySelector('main') || document.body;
  const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden'; };
  const txt = el => (el.innerText || '').replace(/\s+/g, ' ').trim();
  const headings = [...root.querySelectorAll('h1,h2,h3')].filter(vis).map(h => [h.tagName.toLowerCase(), txt(h)]).filter(h => h[1]);
  const items = [...root.querySelectorAll('li, article, [class*="card" i]')].filter(vis).map(txt).filter(t => t && t.length < 400);
  const images = [...root.querySelectorAll('img')].map(i => ({alt: i.getAttribute('alt') || '',
      src: (i.currentSrc || i.src || '').split('?')[0].split('/').pop()}));
  return {headings, items: [...new Set(items)], images};
}
"""


def capture(site, routes=ROUTES, executable=None):
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900})
        for r in routes:
            page.goto(site + r, wait_until="networkidle")
            page.wait_for_timeout(500)
            out[r] = page.evaluate(EXTRACT_JS)
        b.close()
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    exe = os.environ.get("CHROME_BIN") if os.environ.get("CHROME_BIN") and Path(os.environ["CHROME_BIN"]).exists() else None
    try:
        data = capture(a.site)
    except Exception:
        data = capture(a.site, executable=exe)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print({r: (len(v["headings"]), len(v["items"]), len(v["images"])) for r, v in data.items()})
