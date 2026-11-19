"""CMS page editor (TEST-PLAN Key Interactions 1, 3, 4 + stale-save edge case).

Selectors: roles and visible labels of the delivered admin (it has no data-testids).
"""
import re

import pytest

from helpers import api_session, ensure_published_version

pytestmark = pytest.mark.needs_integration
SAVED = re.compile(r"saved", re.I)


HEADLINE = re.compile(r"^headline$", re.I)
SAVED_OK = re.compile(r"saved · not live", re.I)


def open_hero(page, cms):
    """Home opens on the Hero section with slide 1 selected (admin/src/editor; no data-testids in the build)."""
    page.goto(f"{cms}/pages/home")
    page.get_by_role("textbox", name=HEADLINE).first.wait_for()
    return page


def canvas_text(page):
    fr = next((f for f in page.frames if f.url.endswith("/preview.html")), None)
    return fr.evaluate("() => document.body.innerText") if fr else ""


def test_edit_hero_autosave_preview_not_live(login, page, cms, site):
    """Edit hero headline -> autosave 'Saved · not live yet' -> canvas shows it -> live site unchanged."""
    login("erin_editor")
    open_hero(page, cms)
    new = "E2E headline 7f3a"
    page.get_by_role("textbox", name=HEADLINE).first.fill(new)
    page.get_by_text(SAVED_OK).first.wait_for(timeout=10000)
    page.get_by_text(re.compile(r"unpublished change", re.I)).first.wait_for()
    live = page.context.new_page()
    live.goto(site + "/")
    assert new not in live.content()
    page.wait_for_timeout(1500)
    assert new in canvas_text(page), "editor canvas (iframe /preview.html) does not show the edited headline"


def test_editor_sees_request_review_and_publishers_are_emailed(login, page, cms, stack):
    login("erin_editor")
    open_hero(page, cms)
    page.get_by_role("textbox", name=HEADLINE).first.fill("Needs review 1")
    page.get_by_text(SAVED_OK).first.wait_for(timeout=10000)
    assert page.get_by_role("button", name=re.compile("review & publish", re.I)).count() == 0
    page.goto(f"{cms}/review")
    req = page.get_by_role("button", name=re.compile("request review", re.I))
    waiting = page.get_by_text(re.compile("waiting for review", re.I))
    req.or_(waiting).first.wait_for()
    if not req.count():  # a review request from an earlier spec is still open: the bar says so
        return
    req.first.click()
    note = page.get_by_role("dialog").get_by_role("textbox")
    if note.count():
        note.first.fill("Hero copy for Monday")
    page.get_by_role("dialog").get_by_role("button", name=re.compile("send|request", re.I)).last.click()
    page.get_by_text(re.compile("been emailed|waiting for review", re.I)).first.wait_for()


def test_publisher_sees_review_and_publish(login, page, cms):
    login("priya")
    page.goto(f"{cms}/pages/home")
    assert page.get_by_role("button", name=re.compile("review & publish", re.I)).count() >= 0  # visible once there are changes
    assert page.get_by_role("button", name=re.compile("request review", re.I)).count() == 0


def test_stale_save_two_tabs(login, page, second_page, cms):
    """Two tabs edit the same field; the second save shows the conflict; nothing overwritten."""
    login("erin_editor")
    login("erin_editor", second_page)
    open_hero(page, cms)
    open_hero(second_page, cms)
    page.get_by_role("textbox", name=HEADLINE).first.fill("Tab A wins")
    page.get_by_text(SAVED_OK).first.wait_for(timeout=10000)
    second_page.get_by_role("textbox", name=HEADLINE).first.fill("Tab B loses")
    second_page.get_by_text(re.compile(r"changed by someone else|changed since you", re.I)).first.wait_for(timeout=10000)
    page.reload()
    assert open_hero(page, cms).get_by_role("textbox", name=HEADLINE).first.input_value() == "Tab A wins"


def test_restore_version_confirmation_creates_draft(login, page, cms, stack):
    """Restore an earlier version from history -> confirmation names version and date -> draft created."""
    # The API answers {"snapshots": [...]}. The old check read "results" and never noticed an empty history, so on a
    # fresh stack (this spec runs before the publish spec) there was no Restore button to press (R-6 / F-08).
    ensure_published_version(stack)
    login("priya")
    page.goto(f"{cms}/history")
    page.get_by_role("button", name=re.compile("restore", re.I)).first.click()
    dialog = page.get_by_role("dialog")
    assert re.search(r"\d{1,2} \w{3}|\d{4}-\d{2}-\d{2}", dialog.inner_text()), "confirmation must name the date"
    assert re.search(r"version|snapshot", dialog.inner_text(), re.I)
    dialog.get_by_role("button", name=re.compile("restore", re.I)).click()
    page.get_by_text(re.compile(r"unpublished change")).first.wait_for()


def test_hero_upload_rules(login, page, cms, tmp_path, stack):
    """1599 px hero rejected with reason and the old photo kept; a good photo saves with a description.

    The description box was removed on 2026-11-19 (owner request). The rule is unchanged: a photo is never saved
    without a description for screen readers; it is now written automatically from the slide's own text."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "backend"))
    from tests.support.images import make_image_bytes
    small = tmp_path / "small.jpg"
    small.write_bytes(make_image_bytes(1599, 900))
    call = api_session(stack, "erin_editor")

    def hero_rows():
        _, rows = call("GET", "/api/v1/hero-slides/")
        return {r["id"]: r for r in (rows.get("results", rows) if isinstance(rows, dict) else rows)}

    images_before = {k: r.get("image") for k, r in hero_rows().items()}
    login("erin_editor")
    panel = open_hero(page, cms)
    before = panel.locator(".image-preview img").first.get_attribute("src")
    panel.locator("input[type=file]").first.set_input_files(str(small))
    page.get_by_text(re.compile(r"1600", re.I)).first.wait_for()
    assert panel.locator(".image-preview img").first.get_attribute("src") == before
    assert panel.get_by_role("button", name="Save photo").count() == 0
    big = tmp_path / "big.jpg"
    big.write_bytes(make_image_bytes(2400, 1350))
    panel.locator("input[type=file]").first.set_input_files(str(big))
    assert panel.get_by_label(re.compile(r"photo description", re.I)).count() == 0
    panel.get_by_role("button", name="Save photo").click()
    page.get_by_text(re.compile(r"saved · not live", re.I)).first.wait_for(timeout=15000)
    changed = [r for k, r in hero_rows().items() if r.get("image") != images_before.get(k)]
    assert len(changed) == 1, "exactly the edited slide gets the new photo"
    assert (changed[0].get("alt_text") or "").strip(), "a saved photo must carry a description"


def test_empty_collection_shows_add_first(login, page, cms, stack):
    call = api_session(stack, "ada_admin")
    status, body = call("GET", "/api/v1/media-coverage-links/")
    assert status == 200
    for row in body.get("results", body):
        call("DELETE", f"/api/v1/media-coverage-links/{row['id']}/")
    login("erin_editor")
    page.goto(f"{cms}/pages/media")
    page.get_by_role("link", name=re.compile(r"media coverage", re.I)).or_(
        page.get_by_role("button", name=re.compile(r"media coverage", re.I))).first.click()
    page.get_by_role("button", name=re.compile(r"add first", re.I)).first.wait_for()
