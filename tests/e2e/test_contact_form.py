"""Key Interaction 7: contact form — blur validation, send, success message; mailto fallback when the relay is down."""
import os
import re

import pytest

pytestmark = pytest.mark.needs_integration


def test_blur_validation_send_success(page, site):
    page.goto(site + "/contact")
    email = page.get_by_role("textbox", name=re.compile("^email", re.I))
    email.fill("not-an-email")
    email.blur()
    page.get_by_text(re.compile(r"email address like", re.I)).wait_for()
    email.fill("visitor@example.test")
    page.get_by_text(re.compile(r"email address like", re.I)).wait_for(state="hidden")
    page.get_by_role("textbox", name=re.compile("^your name", re.I)).fill("E2E Visitor")
    page.get_by_role("textbox", name=re.compile("^message", re.I)).fill("<b>hello</b> from the E2E suite")
    if not os.environ.get("E2E_TURNSTILE_REACHABLE"):
        pytest.skip("send needs Cloudflare Turnstile (widget + siteverify); not reachable from the sandbox")
    page.get_by_role("button", name=re.compile("send", re.I)).click()
    page.get_by_text(re.compile(r"sending", re.I)).first.wait_for(timeout=3000)
    page.get_by_text(re.compile(r"(sent|thank)", re.I)).first.wait_for(timeout=15000)


def test_relay_down_shows_mailto(page, site):
    page.route(re.compile(r".*/api/v1/contact/.*"), lambda r: r.abort())
    page.goto(site + "/contact")
    page.get_by_role("textbox", name=re.compile("^your name", re.I)).fill("E2E")
    page.get_by_role("textbox", name=re.compile("^email", re.I)).fill("v@example.test")
    page.get_by_role("textbox", name=re.compile("^message", re.I)).fill("relay down test")
    page.get_by_role("button", name=re.compile("send", re.I)).click()
    assert page.locator("a[href^='mailto:']").first.is_visible()
