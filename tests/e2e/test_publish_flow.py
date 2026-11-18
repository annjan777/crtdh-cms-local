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
    marker = f"Published by E2E {int(time.time())}"
    login("priya")
    page.goto(f"{cms}/pages/home")
    page.get_by_test_id("section-home.hero").first.click()
    page.get_by_test_id("field-panel").get_by_label(re.compile("heading", re.I)).first.fill(marker)
    page.get_by_test_id("save-status").filter(has_text=re.compile("saved", re.I)).wait_for()
    assert marker not in urllib.request.urlopen(site + "/").read().decode()
    page.get_by_role("button", name=re.compile("review & publish", re.I)).click()
    assert page.get_by_text(marker).count() >= 1, "review screen must list the change"
    page.get_by_role("button", name=re.compile(r"^publish", re.I)).click()
    status = page.get_by_test_id("publish-status")
    for label in ["queued|waiting", "building", "uploading", r"live at \d{1,2}:\d{2}"]:
        status.filter(has_text=re.compile(label, re.I)).wait_for(timeout=180_000)
    assert marker in urllib.request.urlopen(site + "/").read().decode()


def test_publish_state_sequence_api(stack):
    call = api_session(stack, "priya")
    s, body = call("POST", "/api/v1/cms/publish/", {})
    assert s in (202, 409)
    pid = body["publish_id"] if s == 202 else body.get("publish_id")
    st, seen = wait_status(call, pid, "live")
    assert st["status"] == "live", st
    order = ["queued", "building", "ready_for_upload", "uploading", "live"]
    assert [x for x in order if x in seen] == [x for x in seen if x in order], seen
    assert st["live_at"]


def test_double_click_publish_one_build(stack):
    call = api_session(stack, "priya")
    s1, b1 = call("POST", "/api/v1/cms/publish/", {})
    s2, b2 = call("POST", "/api/v1/cms/publish/", {})
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
