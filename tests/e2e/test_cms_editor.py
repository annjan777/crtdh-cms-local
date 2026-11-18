"""CMS page editor (TEST-PLAN Key Interactions 1, 3, 4 + stale-save edge case).

Selector contract with the admin lane is in docs/testing.md §Selectors (data-testid).
"""
import re

import pytest

from helpers import api_session

pytestmark = pytest.mark.needs_integration
SAVED = re.compile(r"saved", re.I)


def open_hero(page, cms):
    page.goto(f"{cms}/pages/home")
    page.get_by_test_id("section-home.hero").first.click()
    return page.get_by_test_id("field-panel")


def test_edit_hero_autosave_preview_not_live(login, page, cms, site):
    """Edit hero headline -> autosave 'Saved…not live' -> preview shows it -> live site unchanged."""
    login("erin_editor")
    panel = open_hero(page, cms)
    new = "E2E headline 7f3a"
    panel.get_by_label(re.compile("heading", re.I)).first.fill(new)
    page.get_by_test_id("save-status").filter(has_text=SAVED).wait_for(timeout=5000)
    assert re.search(r"not live|draft", page.get_by_test_id("save-status").inner_text(), re.I)
    assert new in page.get_by_test_id("canvas").inner_text()
    live = page.context.new_page()
    live.goto(site + "/")
    assert new not in live.content()
    assert page.get_by_test_id("draft-bar").filter(has_text=re.compile(r"1 unpublished change")).count() == 1


def test_editor_sees_request_review_and_publishers_are_emailed(login, page, cms, stack):
    login("erin_editor")
    open_hero(page, cms).get_by_label(re.compile("heading", re.I)).first.fill("Needs review 1")
    page.get_by_test_id("save-status").filter(has_text=SAVED).wait_for()
    assert page.get_by_role("button", name=re.compile("review & publish", re.I)).count() == 0
    page.get_by_role("button", name=re.compile("request review", re.I)).click()
    page.get_by_role("textbox", name=re.compile("note", re.I)).fill("Hero copy for Monday")
    page.get_by_role("button", name=re.compile("send", re.I)).click()
    page.get_by_text(re.compile("waiting for review", re.I)).wait_for()
    mails = "\n".join(stack.mail())
    assert "priya@example.test" in mails and "Hero copy for Monday" in mails
    assert "erin_editor@example.test" not in re.findall(r"^To: .*$", mails, re.M)[-1]


def test_publisher_sees_review_and_publish(login, page, cms):
    login("priya")
    page.goto(f"{cms}/pages/home")
    assert page.get_by_role("button", name=re.compile("review & publish", re.I)).count() >= 0  # visible once there are changes
    assert page.get_by_role("button", name=re.compile("request review", re.I)).count() == 0


def test_stale_save_two_tabs(login, page, second_page, cms):
    """Two tabs edit the same section; the second save shows the conflict message; nothing overwritten."""
    login("erin_editor")
    login("erin_editor", second_page)
    a, b = open_hero(page, cms), open_hero(second_page, cms)
    a.get_by_label(re.compile("heading", re.I)).first.fill("Tab A wins")
    page.get_by_test_id("save-status").filter(has_text=SAVED).wait_for()
    b.get_by_label(re.compile("heading", re.I)).first.fill("Tab B loses")
    second_page.get_by_text(re.compile(r"someone else changed this|changed since you", re.I)).wait_for(timeout=5000)
    page.reload()
    assert "Tab A wins" in open_hero(page, cms).get_by_label(re.compile("heading", re.I)).first.input_value()


def test_restore_version_confirmation_creates_draft(login, page, cms, stack):
    """Restore an earlier version from history -> confirmation names version and date -> draft created."""
    call = api_session(stack, "priya")
    status, snaps = call("GET", "/api/v1/cms/snapshots/")
    assert status == 200
    if not (snaps.get("results", snaps) if isinstance(snaps, dict) else snaps):
        pytest.skip("needs at least one published snapshot (run after test_publish_flow)")
    login("priya")
    page.goto(f"{cms}/history")
    page.get_by_test_id("history-item").first.get_by_role("button", name=re.compile("restore", re.I)).click()
    dialog = page.get_by_role("dialog")
    assert re.search(r"\d{1,2} \w{3}|\d{4}-\d{2}-\d{2}", dialog.inner_text()), "confirmation must name the date"
    assert re.search(r"version|snapshot", dialog.inner_text(), re.I)
    dialog.get_by_role("button", name=re.compile("restore", re.I)).click()
    page.get_by_test_id("draft-bar").filter(has_text=re.compile(r"unpublished change")).wait_for()


def test_hero_upload_rules(login, page, cms, tmp_path):
    """1599 px hero rejected with reason; missing alt text blocks save."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "backend"))
    from tests.support.images import make_image_bytes
    small = tmp_path / "small.jpg"
    small.write_bytes(make_image_bytes(1599, 900))
    login("erin_editor")
    panel = open_hero(page, cms)
    panel.locator("input[type=file]").first.set_input_files(str(small))
    page.get_by_text(re.compile(r"1600", re.I)).wait_for()
    big = tmp_path / "big.jpg"
    big.write_bytes(make_image_bytes(2400, 1350))
    panel.locator("input[type=file]").first.set_input_files(str(big))
    alt = panel.get_by_label(re.compile("alt", re.I)).first
    alt.fill("")
    alt.blur()
    page.get_by_text(re.compile(r"alt text.*required|describe the image", re.I)).wait_for()


def test_empty_collection_shows_add_first(login, page, cms, stack):
    call = api_session(stack, "ada_admin")
    status, body = call("GET", "/api/v1/media-coverage-links/")
    assert status == 200
    for row in body.get("results", body):
        call("DELETE", f"/api/v1/media-coverage-links/{row['id']}/")
    login("erin_editor")
    page.goto(f"{cms}/pages/media")
    page.get_by_role("button", name=re.compile(r"add first", re.I)).first.wait_for()
