"""Diff vs the last published snapshot, discard, restore (plan WS1.2, WS3.4)."""
import pytest

from apps.carousel.models import HeroSlide
from apps.core.models import HomePage, NewsItem
from apps.publishing import changes
from apps.publishing import content as cms
from apps.publishing.audit import WriteContext
from apps.publishing.errors import CMSError
from apps.publishing.models import AuditEntry
from tests.support.errors import assert_contract_error

pytestmark = pytest.mark.django_db


def by_item(result):
    return {c["item_id"]: c for p in result["pages"] for c in p["changes"]}


def test_no_changes_right_after_baseline(baseline):
    assert changes.pending_changes() == {"count": 0, "pages": [], "review_request": None}


def test_without_baseline_everything_is_added(content):
    result = changes.pending_changes()
    assert result["count"] > 0
    assert {c["kind"] for p in result["pages"] for c in p["changes"]} <= {"added", "changed"}


def test_diff_kinds_and_authors(baseline, editor, publisher):
    ed = WriteContext(user=editor)
    mcp = WriteContext(user=publisher, channel="mcp", connector_session="claude-7")
    cms.update_item("hero-slides", 18, {"heading": "New headline"}, ctx=ed, expected_version=1)
    cms.update_item("hero-slides", 19, {"is_published": False}, ctx=mcp, expected_version=1)
    added = cms.create_item("news-items", {"text": "Health camp on 2 Dec", "order": 10, "is_published": True}, ctx=mcp)
    removed = NewsItem.objects.order_by("id").first()
    cms.delete_item("news-items", removed.pk, ctx=ed)
    cms.update_item("home-page", 1, {"women_text_1": "Updated women text"}, ctx=ed, expected_version=1)
    result = changes.pending_changes()
    items = by_item(result)
    assert result["count"] == 5

    hero = items["home.hero.hero-slides:18"]
    assert hero["kind"] == "changed"
    before = {r["id"]: r for r in baseline.data["collections"]["hero-slides"]}[18]["heading"]
    assert hero["fields"] == [{"name": "heading", "label": "Headline", "before": before, "after": "New headline"}]
    assert hero["section"] == "Hero" and hero["session_id"] is None
    assert (hero["author"], hero["channel"]) == ("erin_editor", "admin")
    assert hero["label"] == "New headline"

    hidden = items["home.hero.hero-slides:19"]
    assert hidden["kind"] == "hidden" and hidden["fields"][0] == {"name": "is_published", "label": "Visible on the site",
                                                                 "before": True, "after": False}
    assert (hidden["author"], hidden["channel"], hidden["session_id"]) == ("priya", "mcp", "claude-7")

    new = items[f"home.news.news-items:{added.pk}"]
    assert new["kind"] == "added" and {"name": "text", "label": "News line", "before": None,
                                     "after": "Health camp on 2 Dec"} in new["fields"]
    gone = items[f"home.news.news-items:{removed.pk}"]
    assert gone["kind"] == "removed" and gone["author"] == "erin_editor"

    women = items["home.rural.home-page:1"]
    assert women["kind"] == "changed" and women["fields"][0]["name"] == "women_text_1"
    assert [p["page"] for p in result["pages"]] == ["home"]

    only_session = changes.pending_changes(session_id="claude-7")
    assert set(by_item(only_session)) == {"home.hero.hero-slides:19", f"home.news.news-items:{added.pk}"}
    only_author = changes.pending_changes(author="erin_editor")
    assert set(by_item(only_author)) == {"home.hero.hero-slides:18", f"home.news.news-items:{removed.pk}",
                                         "home.rural.home-page:1"}


def test_hidden_item_never_published_is_not_a_change(baseline, editor):
    ctx = WriteContext(user=editor)
    cms.create_item("news-items", {"text": "Draft only", "order": 3, "is_published": False}, ctx=ctx)
    assert changes.pending_changes()["count"] == 0


def test_discard_each_kind(baseline, editor):
    ctx = WriteContext(user=editor)
    original = HeroSlide.objects.get(pk=18).heading
    cms.update_item("hero-slides", 18, {"heading": "Oops"}, ctx=ctx, expected_version=1)
    cms.update_item("hero-slides", 19, {"is_published": False}, ctx=ctx, expected_version=1)
    added = cms.create_item("news-items", {"text": "Temp", "order": 10, "is_published": True}, ctx=ctx)
    removed = NewsItem.objects.order_by("id").first()
    removed_text = removed.text
    cms.delete_item("news-items", removed.pk, ctx=ctx)
    cms.update_item("home-page", 1, {"women_text_1": "Changed", "objective_text": "Also changed"}, ctx=ctx,
                    expected_version=1)

    for iid in ["home.hero.hero-slides:18", "home.hero.hero-slides:19", f"home.news.news-items:{added.pk}",
                f"home.news.news-items:{removed.pk}", "home.rural.home-page:1"]:
        assert changes.discard_item(iid, ctx=ctx) is True

    assert HeroSlide.objects.get(pk=18).heading == original
    assert HeroSlide.objects.get(pk=18).version == 3  # discard is a write too
    assert HeroSlide.objects.get(pk=19).is_published is True
    assert not NewsItem.objects.filter(pk=added.pk).exists()
    assert NewsItem.objects.get(pk=removed.pk).text == removed_text  # re-created with the same pk
    home = HomePage.load()
    assert home.objective_text == "Also changed"  # other section untouched
    remaining = changes.pending_changes()
    assert set(by_item(remaining)) == {"home.objective.home-page:1"}
    assert AuditEntry.objects.filter(action="discard").count() == 5
    assert changes.discard_item("home.hero.hero-slides:18", ctx=ctx) is False  # already clean


def test_discard_recreates_removed_parent(baseline, editor):
    from apps.innovations.models import Innovation, InnovationImage
    ctx = WriteContext(user=editor)
    image = InnovationImage.objects.first()
    parent_id = image.innovation_id
    cms.delete_item("innovations", parent_id, ctx=ctx)  # cascades the image
    assert not InnovationImage.objects.filter(pk=image.pk).exists()
    changes.discard_item(f"innovations.list.innovation-images:{image.pk}", ctx=ctx)
    assert Innovation.objects.filter(pk=parent_id).exists() and InnovationImage.objects.filter(pk=image.pk).exists()


def test_discard_session(baseline, editor, publisher):
    mcp = WriteContext(user=editor, channel="mcp", connector_session="sess-a")
    other = WriteContext(user=publisher)
    cms.update_item("hero-slides", 18, {"heading": "Claude 1"}, ctx=mcp, expected_version=1)
    cms.update_item("hero-slides", 18, {"heading": "Claude 2"}, ctx=mcp, expected_version=2)
    made = cms.create_item("news-items", {"text": "Claude news", "order": 4, "is_published": True}, ctx=mcp)
    cms.update_item("hero-slides", 20, {"heading": "Human"}, ctx=other, expected_version=1)
    reverted = changes.discard_session("sess-a", ctx=WriteContext(user=editor))
    assert set(reverted) == {"home.hero.hero-slides:18", f"home.news.news-items:{made.pk}"}
    assert set(by_item(changes.pending_changes())) == {"home.hero.hero-slides:20"}


def test_discard_without_baseline_refuses(content, editor):
    with pytest.raises(CMSError) as exc:
        changes.discard_item("home.hero.hero-slides:18", ctx=WriteContext(user=editor))
    assert exc.value.code == "CMS_VALIDATION"


def test_restore_snapshot_copies_values_back_as_changes(baseline, editor):
    ctx = WriteContext(user=editor)
    cms.update_item("hero-slides", 18, {"heading": "Later"}, ctx=ctx, expected_version=1)
    later = cms.create_item("news-items", {"text": "Added later", "order": 7, "is_published": True}, ctx=ctx)
    victim = NewsItem.objects.order_by("id").first()
    cms.delete_item("news-items", victim.pk, ctx=ctx)
    count = changes.restore_snapshot(baseline, ctx=ctx)
    assert count == 3
    assert NewsItem.objects.get(pk=later.pk).is_published is False  # hidden, never deleted
    assert NewsItem.objects.filter(pk=victim.pk).exists()
    assert changes.pending_changes()["count"] == 0
    assert AuditEntry.objects.filter(action="restore").count() == 3


# ---- HTTP -------------------------------------------------------------------------------------------------------
def test_changes_and_discard_endpoints(api_as, baseline):
    client = api_as("editor")
    client.patch("/api/v1/hero-slides/18/", {"heading": "Edited", "expected_version": 1}, format="json")
    resp = client.get("/api/v1/cms/changes/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    change = body["pages"][0]["changes"][0]
    assert set(change) >= {"item_id", "resource", "pk", "label", "kind", "fields", "author", "channel", "at",
                           "session_id", "section"}
    assert body["review_request"] is None
    resp = client.post("/api/v1/cms/changes/discard/", {"item_id": change["item_id"]}, format="json")
    assert resp.status_code == 200
    assert resp.json() | {"pages": []} == {"reverted": [change["item_id"]], "discarded": 1, "pending": 0, "count": 0,
                                         "pages": [], "review_request": None}
    assert_contract_error(client.post("/api/v1/cms/changes/discard/", {}, format="json"), "CMS_VALIDATION")
    assert_contract_error(client.post("/api/v1/cms/changes/discard/", {"item_id": "bogus"}, format="json"),
                          "CMS_NOT_FOUND")


def test_snapshot_restore_endpoint_is_publisher_only(api_as, baseline):
    url = f"/api/v1/cms/snapshots/{baseline.pk}/restore/"
    assert_contract_error(api_as("editor").post(url, {}, format="json"), "CMS_FORBIDDEN_ROLE")
    resp = api_as("publisher").post(url, {}, format="json")
    assert resp.status_code == 200 and resp.json()["snapshot_id"] == baseline.snapshot_id
    listing = api_as("editor").get("/api/v1/cms/snapshots/").json()["snapshots"]
    assert listing[0]["snapshot_id"] == baseline.snapshot_id and listing[0]["counts"]["hero-slides"] == 3
    assert listing[0]["is_live"] is True and set(listing[0]) >= {"id", "published_at", "published_by", "note"}
