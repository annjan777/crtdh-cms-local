"""The in-process functions the MCP adapter (mcp_server/cms.py) calls, under their agreed names."""
import pytest

from apps.publishing import changes, registry, review, uploads
from apps.publishing import content as cms
from apps.publishing.audit import WriteContext
from apps.publishing.errors import CMSError
from apps.publishing.models import AuditEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def mcp(editor):
    return WriteContext(user=editor, channel="mcp", connector_session="claude-session-1")


def test_create_item_in_section_applies_page_filter_and_starts_hidden(content, mcp):
    obj = cms.create_item("image-grid-blocks", {"section_title": "Camp photos"}, ctx=mcp,
                              section_id="covid-19.photo-sections")
    assert obj.page == "covid-19" and obj.is_published is False
    iid = registry.item_id("image-grid-blocks", obj.pk, obj)
    assert iid == f"covid-19.photo-sections.image-grid-blocks:{obj.pk}"
    e = AuditEntry.objects.get(action="create")
    assert (e.channel, e.connector_session, e.item_id) == ("mcp", "claude-session-1", iid)
    with pytest.raises(CMSError) as exc:
        cms.create_item("image-grid-blocks", {"bogus": 1}, ctx=mcp, section_id="covid-19.photo-sections")
    assert exc.value.code == "CMS_VALIDATION"
    with pytest.raises(CMSError) as exc:
        cms.create_item("home-page", {}, ctx=mcp, section_id="home.objective")
    assert exc.value.code == "CMS_VALIDATION"
    with pytest.raises(CMSError) as exc:
        cms.create_item("news-items", {"text": "x"}, ctx=mcp, section_id="home.hero")
    assert exc.value.code == "CMS_NOT_FOUND"


def test_update_by_item_id_child_and_alt_fields(content, mcp):
    from apps.innovations.models import InnovationImage
    img = InnovationImage.objects.first()
    obj = cms.update_by_item_id(f"innovations.list.innovation-images:{img.pk}",
                                    {"caption": "Lab bench", "image_alt": "A lab bench"}, ctx=mcp,
                                    expected_version=img.version)
    assert (obj.caption, obj.image_alt) == ("Lab bench", "A lab bench")
    home = cms.update_by_item_id("home.enterprises.home-page:1", {"enterprises_image_1_alt": "Workers"},
                                     ctx=mcp, expected_version=1)
    assert home.enterprises_image_1_alt == "Workers"
    with pytest.raises(CMSError) as exc:  # a field of another section of the same singleton
        cms.update_by_item_id("home.enterprises.home-page:1", {"objective_text": "x"}, ctx=mcp,
                                  expected_version=home.version)
    assert exc.value.code == "CMS_VALIDATION"


def test_stale_error_body_has_editor(content, mcp, publisher):
    cms.update_by_item_id("home.hero.hero-slides:18", {"heading": "One"}, ctx=WriteContext(user=publisher),
                              expected_version=1)
    with pytest.raises(CMSError) as exc:
        cms.update_by_item_id("home.hero.hero-slides:18", {"heading": "Two"}, ctx=mcp, expected_version=1)
    body = exc.value.body
    assert body["code"] == "CMS_STALE_VERSION" and body["current_version"] == 2 and body["edited_by"] == "priya"


def test_reorder_accepts_item_ids(content, mcp):
    from apps.core.models import NewsItem
    ids = list(NewsItem.objects.order_by("order", "id").values_list("id", flat=True))
    cms.reorder("news-items", [f"home.news.news-items:{pk}" for pk in reversed(ids)], ctx=mcp)
    assert list(NewsItem.objects.order_by("order", "id").values_list("id", flat=True)) == list(reversed(ids))
    with pytest.raises(CMSError):
        cms.reorder("news-items", ["home.hero.hero-slides:18"], ctx=mcp)
    with pytest.raises(CMSError):
        cms.reorder("news-items", [999999], ctx=mcp)


def test_attach_media_accepts_media_prefix(content, mcp, media_root):
    from django.core.files.base import ContentFile

    from apps.publishing.models import MediaAsset
    from tests.support.images import make_image_bytes
    big = MediaAsset()
    big.file.save("big.jpg", ContentFile(make_image_bytes(2400, 1350)))
    obj = cms.attach_media("hero-slides", 18, "image", f"media:{big.pk}", ctx=mcp, expected_version=1)
    assert obj.image.name == big.file.name
    with pytest.raises(CMSError) as exc:
        cms.attach_media("hero-slides", 18, "heading", big.pk, ctx=mcp, expected_version=2)
    assert exc.value.code == "CMS_VALIDATION"


def test_session_scoped_changes_and_discard(content, mcp, editor):
    from django.core.management import call_command
    call_command("create_baseline_snapshot", stdout=open("/dev/null", "w"))  # noqa: SIM115
    cms.update_by_item_id("home.hero.hero-slides:18", {"heading": "Claude edit"}, ctx=mcp, expected_version=1)
    cms.update_by_item_id("home.hero.hero-slides:19", {"heading": "Human edit"}, ctx=WriteContext(user=editor),
                              expected_version=1)
    mine = changes.pending_changes(session_id="claude-session-1")
    assert [c["item_id"] for p in mine["pages"] for c in p["changes"]] == ["home.hero.hero-slides:18"]
    assert mine["pages"][0]["changes"][0]["session_id"] == "claude-session-1"
    assert changes.discard_item("home.hero.hero-slides:18", ctx=mcp) is True
    cms.update_by_item_id("home.hero.hero-slides:20", {"heading": "Claude again"}, ctx=mcp, expected_version=1)
    assert changes.discard_session("claude-session-1", ctx=mcp) == ["home.hero.hero-slides:20"]
    assert [c["item_id"] for p in changes.pending_changes()["pages"] for c in p["changes"]] == \
        ["home.hero.hero-slides:19"]


def test_review_upload_and_preview_names(content, mcp, editor, publisher, mail_outbox):
    rr = review.request_review(editor, "From Claude", ctx=mcp)
    assert rr.pk and "(through Claude)" in mail_outbox[0].body
    link = uploads.create_upload_link(editor, ctx=mcp, min_width=1600)
    assert set(link) == {"url", "token", "expires_at"}
    assert uploads.link_status(link["token"])["used"] is False
    assert registry.preview_url("home.hero.hero-slides:18").endswith("/pages/home?item=home.hero.hero-slides:18")
