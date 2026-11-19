"""Critical path: edit -> preview -> publish -> static site changed (Playwright + fake SFTP + publish agent).
Key Interaction 2: queued -> building -> uploading -> 'Live at hh:mm'.

Requires the preprod-style stack: publish worker + local SFTP (port 2223) + publish agent, i.e. run with
--external against scripts/preprod.sh, or set E2E_PUBLISH_STACK=1 after starting those pieces.
"""
import os
import re
import time
import urllib.request

import pytest

from helpers import api_session

pytestmark = pytest.mark.needs_integration


@pytest.fixture(scope="module", autouse=True)
def _requires_publish_stack(stack):
    if not (os.environ.get("E2E_PUBLISH_STACK") == "1"):
        pytest.skip("needs publish worker + SFTP + agent (scripts/preprod.sh then --external, or E2E_PUBLISH_STACK=1)")


def wait_status(call, publish_id, want, timeout=180):
    seen = []
    end = time.time() + timeout
    while time.time() < end:
        _, st = call("GET", f"/api/v1/cms/publish/{publish_id}/")
        if not seen or seen[-1] != st["status"]:
            seen.append(st["status"])
        if st["status"] in (want, "failed"):
            return st, seen
        time.sleep(1)
    raise AssertionError(f"publish {publish_id} stuck; states seen {seen}")


def test_edit_preview_publish_static_changed(login, page, cms, site, stack):
    """Edit in the page editor -> not live -> Review & publish -> Queued/Building/Uploading -> Live at hh:mm ->
    the static site on the fake CIC host shows the change."""
    marker = f"Published by E2E {int(time.time())}"
    login("priya")
    page.goto(f"{cms}/pages/home")
    field = page.get_by_role("textbox", name=re.compile(r"^headline$", re.I)).first
    field.fill(marker)
    page.get_by_text(re.compile(r"saved · not live", re.I)).first.wait_for(timeout=10000)
    assert marker not in urllib.request.urlopen(site + "/").read().decode()
    page.goto(f"{cms}/review")
    page.get_by_text(marker).first.wait_for()
    page.get_by_role("button", name=re.compile(r"^publish \d+ change", re.I)).click()
    guard = page.get_by_role("dialog").filter(has_text=re.compile("shorter list", re.I))
    page.wait_for_timeout(1500)
    if guard.count():  # another spec emptied a collection on purpose; the guard asks first (that is the feature)
        guard.get_by_role("button").filter(has_text=re.compile("publish", re.I)).last.click()
    page.get_by_text(re.compile(r"live at \d{1,2}:\d{2}", re.I)).first.wait_for(timeout=300_000)
    assert marker in urllib.request.urlopen(site + "/").read().decode()


def _change_and_publish(call):
    """Make one draft change (so there is something to publish) and start a publish; guard-confirmed because
    other specs empty a collection on purpose."""
    _, rows = call("GET", "/api/v1/hero-slides/")
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    r = next(x for x in rows if x.get("is_published"))
    call("PATCH", f"/api/v1/hero-slides/{r['id']}/", {"heading": f"API publish {time.time():.0f}",
                                                       "expected_version": r["version"]})
    return call("POST", "/api/v1/cms/publish/", {"confirm_shrink": True})


def test_publish_state_sequence_api(stack):
    call = api_session(stack, "priya")
    s, body = _change_and_publish(call)
    assert s in (202, 409), (s, body)
    pid = body["publish_id"] if s == 202 else body.get("publish_id")
    st, seen = wait_status(call, pid, "live")
    assert st["status"] == "live", st
    order = ["queued", "building", "ready_for_upload", "uploading", "live"]
    assert [x for x in order if x in seen] == [x for x in seen if x in order], seen
    assert st["live_at"]


def test_double_click_publish_one_build(stack):
    call = api_session(stack, "priya")
    s1, b1 = _change_and_publish(call)
    s2, b2 = call("POST", "/api/v1/cms/publish/", {"confirm_shrink": True})
    assert s1 == 202 and s2 == 409 and b2["code"] == "CMS_PUBLISH_RUNNING"
    assert b1["publish_id"] in b2["message"] or b2.get("publish_id") == b1["publish_id"]
    wait_status(call, b1["publish_id"], "live")


def test_agent_offline_shows_waiting(stack):
    if os.environ.get("E2E_AGENT_STOPPED") != "1":
        pytest.skip("run with the publish agent stopped (E2E_AGENT_STOPPED=1)")
    call = api_session(stack, "priya")
    _, b = call("POST", "/api/v1/cms/publish/", {})
    time.sleep(10)
    _, st = call("GET", f"/api/v1/cms/publish/{b['publish_id']}/")
    assert st["status"] == "ready_for_upload", st  # honest state, never "live" without the agent
    assert "agent_last_seen" in st
