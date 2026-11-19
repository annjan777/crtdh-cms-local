"""Exploratory charters (report-only, scripted because the session browser cannot open localhost):
editor on a phone, keyboard-only sign-in and focus visibility, canvas renders real page text, long/Indic input."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
from helpers import totp_now  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

E = Path("docs/test-evidence/2026-11-19/explore")
E.mkdir(parents=True, exist_ok=True)
users = json.loads(Path(".preprod/users.json").read_text())
notes = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN") or None,
                          args=["--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=localhost;127.0.0.1"])
    ctx = b.new_context(ignore_https_errors=True, viewport={"width": 375, "height": 812})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    page.goto("https://localhost:3600/login")
    page.get_by_label(re.compile("user ?name", re.I)).wait_for()
    # keyboard-only sign-in
    page.keyboard.press("Tab")
    focused = page.evaluate("() => document.activeElement && document.activeElement.id")
    ring = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).boxShadow")
    notes.append(f"first Tab focuses #{focused}; focus style: {ring[:80]}")
    page.keyboard.type("erin_editor")
    page.keyboard.press("Tab")
    page.keyboard.type(os.environ["CRTDH_TEST_PASSWORD"])
    page.keyboard.press("Enter")
    page.get_by_label(re.compile("^code", re.I)).wait_for()
    page.keyboard.type(totp_now(users["erin_editor"]["totp_secret"]))
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile("/pages/"), timeout=20000)
    notes.append("keyboard-only sign-in (Tab/type/Enter, code + Enter) works")
    page.wait_for_timeout(4000)
    page.screenshot(path=str(E / "editor-375.png"), full_page=False)
    ov = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    notes.append(f"editor at 375 px: horizontal overflow {ov}px")
    fr = next((f for f in page.frames if f.url.endswith("/preview.html")), None)
    txt = fr.evaluate("() => document.body.innerText.slice(0, 120)") if fr else ""
    notes.append(f"canvas iframe text at 375: {txt!r}")
    # long + Indic input in the headline field
    hl = page.get_by_role("textbox", name=re.compile(r"^headline$", re.I)).first
    if hl.count():
        before = hl.input_value()
        hl.fill("परीक्षण शीर्षक — একটি দীর্ঘ শিরোনাম যা অনেক লম্বা " * 3)
        page.wait_for_timeout(2500)
        status = page.locator(".save-status").first.inner_text() if page.locator(".save-status").count() else "?"
        notes.append(f"long Hindi/Bengali headline: save status {status!r}")
        page.screenshot(path=str(E / "editor-375-indic.png"))
        hl.fill(before)
        page.wait_for_timeout(2500)
    notes.append(f"page errors: {errs[:3]}")
    b.close()
print("\n".join(notes))
(E / "notes.txt").write_text("\n".join(notes) + "\n")
