"""Does the page editor's canvas (iframe /preview.html) render the page? Logs frame console + messages."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
from helpers import totp_now  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

users = json.loads(Path(".preprod/users.json").read_text())
user = sys.argv[1] if len(sys.argv) > 1 else "ada_admin"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN") or None)
    page = b.new_context(ignore_https_errors=True, viewport={"width": 1440, "height": 900}).new_page()
    logs = []
    page.on("console", lambda m: logs.append(f"{m.type}: {m.text[:200]}"))
    page.on("pageerror", lambda e: logs.append(f"pageerror: {str(e)[:200]}"))
    page.goto("https://localhost:3600/login")
    page.get_by_label(re.compile("user ?name", re.I)).fill(user)
    page.get_by_label(re.compile("password", re.I)).fill(os.environ["CRTDH_TEST_PASSWORD"])
    page.get_by_role("button", name=re.compile("^sign in", re.I)).click()
    page.get_by_label(re.compile("^code", re.I)).fill(totp_now(users[user]["totp_secret"]))
    page.get_by_role("button", name=re.compile(r"^\s*verify", re.I)).click()
    page.wait_for_url(re.compile("/pages/"), timeout=20000)
    page.wait_for_timeout(10000)
    fr = next((f for f in page.frames if f.url.endswith("/preview.html")), None)
    info = fr.evaluate("""() => ({html: document.getElementById('preview-root')?.innerHTML.length,
        text: document.body.innerText.slice(0, 200), h: document.body.scrollHeight})""") if fr else None
    page.screenshot(path="docs/test-evidence/2026-11-19/editor-canvas.png")
    print(json.dumps({"frame": bool(fr), "info": info, "logs": logs[:15]}, indent=1))
    b.close()
