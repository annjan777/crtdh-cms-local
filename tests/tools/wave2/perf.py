"""Lab performance check (gstack:benchmark style): LCP, CLS, JS/CSS/total transfer per page, throttled.
Throttle: Slow-4G-ish (1.6 Mbps down, 750 kbps up, 150 ms RTT) + 4x CPU, cold cache, 375x812 and 1280x900.
    python tests/tools/wave2/perf.py --site https://localhost:3602 --admin https://localhost:3600 --out <json>"""
import argparse
import json
import os

from playwright.sync_api import sync_playwright

OBS = """() => { window.__lcp = 0; window.__cls = 0;
  new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp = e.renderTime || e.loadTime || e.startTime; })
    .observe({type: 'largest-contentful-paint', buffered: true});
  new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
    .observe({type: 'layout-shift', buffered: true}); }"""


def measure(browser, url, viewport, throttle=True):
    ctx = browser.new_context(ignore_https_errors=True, viewport=viewport)
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    if throttle:
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
                 "downloadThroughput": 1.6e6 / 8, "uploadThroughput": 750e3 / 8})
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    sizes = {"js": 0, "css": 0, "img": 0, "font": 0, "doc": 0, "other": 0}
    count = {"requests": 0}

    def on_resp(resp):
        try:
            n = int(resp.headers.get("content-length") or len(resp.body()))
        except Exception:  # noqa: BLE001
            n = 0
        t = resp.request.resource_type
        key = {"script": "js", "stylesheet": "css", "image": "img", "font": "font", "document": "doc"}.get(t, "other")
        sizes[key] += n
        count["requests"] += 1
    page.on("response", on_resp)
    page.add_init_script(f"({OBS})()")
    page.goto(url, wait_until="load", timeout=120000)
    page.wait_for_timeout(2500)
    m = page.evaluate("""() => ({lcp: window.__lcp, cls: window.__cls,
        fcp: (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || 0,
        load: performance.timing.loadEventEnd - performance.timing.navigationStart})""")
    ctx.close()
    return {"url": url, "viewport": f"{viewport['width']}x{viewport['height']}", "lcp_ms": round(m["lcp"]),
            "fcp_ms": round(m["fcp"]), "cls": round(m["cls"], 3), "load_ms": m["load"], "requests": count["requests"],
            **{f"{k}_kb": round(v / 1024, 1) for k, v in sizes.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--admin")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN") or None)
        for path in ("/", "/about", "/team"):
            for vp in ({"width": 375, "height": 812}, {"width": 1280, "height": 900}):
                rows.append(measure(b, a.site + path, vp))
        if a.admin:
            rows.append(measure(b, a.admin + "/login", {"width": 1280, "height": 900}))
        b.close()
    for r in rows:
        print(json.dumps(r))
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
