"""Screenshot all 12 pages + 404 at 375/768/1280 and report overflow and console errors.
Usage: /home/claude/venv/bin/python scripts/screens.py [base_url] [out_dir] [page ids...]"""
import sys, json
from playwright.sync_api import sync_playwright

base = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3100'
out = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/team/screens/frontend'
only = set(sys.argv[3:])
PATHS = ['/', '/about', '/team', '/innovations', '/facilities', '/services', '/product', '/enterprises',
         '/social-impact', '/covid-19', '/media', '/contact', '/this-page-does-not-exist']
report = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    for w in (375, 768, 1280):
        ctx = b.new_context(viewport={'width': w, 'height': 900}, device_scale_factor=1)
        for path in PATHS:
            name = 'home' if path == '/' else ('404' if 'not-exist' in path else path.strip('/'))
            if only and name not in only:
                continue
            page = ctx.new_page()
            errs = []
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'TUNNEL' not in m.text and not ('404' in m.text and 'not-exist' in path) else None)
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.on('requestfailed', lambda r: errs.append('FAILED ' + r.url) if 'localhost' in r.url else None)
            page.goto(base + path, wait_until='networkidle')
            page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); } await Promise.all([...document.images].filter(i => i.offsetParent && !i.complete).map(i => new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 4000) }))); window.scrollTo(0, 0); }""")
            page.wait_for_timeout(300)
            over = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            page.screenshot(path=f'{out}/{name}-{w}.png', full_page=True)
            broken = page.evaluate("[...document.images].filter(i => i.offsetParent && i.complete && i.naturalWidth === 0).map(i => i.src)")
            if broken: errs.append('BROKEN IMG ' + ', '.join(broken[:3]))
            report.append({'page': name, 'w': w, 'overflow': over, 'errors': errs[:3]})
            page.close()
        ctx.close()
    b.close()
bad = [r for r in report if r['overflow'] > 0 or r['errors']]
print(json.dumps(bad, indent=1) if bad else f'{len(report)} shots, no overflow, no console errors')
