"""Optimistic concurrency (contract §3/§4) and the audit log (plan WS1.4)."""
import pytest
from django.test import override_settings

from apps.carousel.models import HeroSlide
from apps.core.models import HomePage
from apps.publishing.models import AuditEntry
from tests.support.errors import assert_contract_error

from .a4 import assert_a4_error

pytestmark = pytest.mark.django_db


def test_rows_expose_version(api_as, content):
    resp = api_as("editor").get("/api/v1/hero-slides/")
    assert resp.status_code == 200
    rows = resp.json()["results"]
    assert all(r["version"] == 1 for r in rows)


def test_stale_save_two_tabs_second_gets_conflict_nothing_overwritten(api_as, content, publisher):
    tab1, tab2 = api_as("editor"), api_as(publisher)
    url = "/api/v1/hero-slides/18/"
    r1 = tab1.patch(url, {"heading": "From tab one", "expected_version": 1}, format="json")
    assert r1.status_code == 200 and r1.json()["version"] == 2
    r2 = tab2.patch(url, {"heading": "From tab two", "expected_version": 1}, format="json")
    body = assert_a4_error(r2, "CMS_STALE_VERSION", current_version=2)
    assert body["edited_by"] == "erin_editor" and body["edited_at"].endswith("Z")
    assert "home.hero.hero-slides:18" in body["message"]
    assert "you sent v1, current v2" in body["message"]
    assert "erin_editor" in body["message"]  # who changed it
    assert HeroSlide.objects.get(pk=18).heading == "From tab one"


def test_update_requires_expected_version(api_as, content):
    resp = api_as("editor").patch("/api/v1/hero-slides/18/", {"heading": "x"}, format="json")
    assert_contract_error(resp, "CMS_VALIDATION", field="expected_version")
    resp = api_as("editor").patch("/api/v1/hero-slides/18/", {"heading": "x", "expected_version": "abc"}, format="json")
    assert_contract_error(resp, "CMS_VALIDATION", field="expected_version")


def test_put_also_checks_version(api_as, content):
    client = api_as("editor")
    row = client.get("/api/v1/news-items/").json()["results"][0]
    data = {k: row[k] for k in ("text", "link_url", "order")}
    assert_a4_error(client.put(f"/api/v1/news-items/{row['id']}/", {**data, "expected_version": 9}, format="json"),
                    "CMS_STALE_VERSION", current_version=1)
    resp = client.put(f"/api/v1/news-items/{row['id']}/", {**data, "text": "New", "expected_version": 1}, format="json")
    assert resp.status_code == 200 and resp.json()["version"] == 2


def test_singleton_versioning(api_as, content):
    client = api_as("editor")
    v = client.get("/api/v1/home-page/").json()["version"]
    ok = client.patch("/api/v1/home-page/", {"objective_text": "New objective", "expected_version": v}, format="json")
    assert ok.status_code == 200 and ok.json()["version"] == v + 1
    stale = client.patch("/api/v1/home-page/", {"objective_text": "Again", "expected_version": v}, format="json")
    body = assert_a4_error(stale, "CMS_STALE_VERSION", current_version=v + 1)
    assert "home.objective.home-page:1" in body["message"]
    assert HomePage.load().objective_text == "New objective"


def test_validation_errors_use_contract_body(api_as, content):
    resp = api_as("editor").patch("/api/v1/hero-slides/18/", {"image_position": "diagonal", "expected_version": 1},
                                  format="json")
    assert_contract_error(resp, "CMS_VALIDATION", field="image_position")
    assert HeroSlide.objects.get(pk=18).version == 1


def test_reorder_bumps_versions_of_moved_rows_and_audits(api_as, content):
    client = api_as("editor")
    ids = [r["id"] for r in client.get("/api/v1/news-items/").json()["results"]]
    resp = client.post("/api/v1/news-items/reorder/", {"order": list(reversed(ids))}, format="json")
    assert resp.status_code == 200
    rows = {r["id"]: r for r in client.get("/api/v1/news-items/").json()["results"]}
    moved = [i for pos, i in enumerate(reversed(ids)) if rows[i]["order"] == pos and rows[i]["version"] == 2]
    assert len(moved) >= 2
    assert AuditEntry.objects.filter(resource="news-items", action="reorder").count() == len(moved)


def test_reorder_rejects_wrong_ids(api_as, content):
    resp = api_as("editor").post("/api/v1/news-items/reorder/", {"order": [1, 2]}, format="json")
    assert_contract_error(resp, "CMS_VALIDATION", field="order")


def test_audit_create_update_delete(api_as, content, editor):
    editor_client, publisher_client = api_as(editor), api_as("publisher")
    created = editor_client.post("/api/v1/news-items/", {"text": "Camp on Sunday", "order": 9}, format="json")
    assert created.status_code == 201
    pk = created.json()["id"]
    editor_client.patch(f"/api/v1/news-items/{pk}/", {"text": "Camp on Monday", "expected_version": 1}, format="json")
    assert publisher_client.delete(f"/api/v1/news-items/{pk}/").status_code == 204
    entries = list(AuditEntry.objects.filter(resource="news-items", pk_value=str(pk)).order_by("id"))
    assert [e.action for e in entries] == ["create", "update", "delete"]
    c, u, d = entries
    assert c.before is None and c.after["text"] == "Camp on Sunday" and c.actor == editor and c.channel == "admin"
    assert u.before["text"] == "Camp on Sunday" and u.after["text"] == "Camp on Monday" and u.after["version"] == 2
    assert d.after is None and d.actor_name == "priya"
    assert c.item_id == f"home.news.news-items:{pk}"


def test_channel_header_from_browser_is_ignored(api_as, content):
    client = api_as("editor")
    client.credentials(HTTP_X_CSRFTOKEN=client.csrf_token, HTTP_X_CMS_CHANNEL="mcp", HTTP_X_CMS_CONNECTOR_SESSION="s1")
    client.patch("/api/v1/hero-slides/18/", {"heading": "x", "expected_version": 1}, format="json")
    entry = AuditEntry.objects.get(resource="hero-slides", pk_value="18")
    assert entry.channel == "admin" and entry.connector_session is None


@override_settings(CMS_INTERNAL_SECRET="internal-test-secret")
def test_channel_header_honoured_for_trusted_internal_caller(api_as, content):
    client = api_as("editor")
    client.credentials(HTTP_X_CSRFTOKEN=client.csrf_token, HTTP_X_CMS_CHANNEL="mcp",
                       HTTP_X_CMS_CONNECTOR_SESSION="sess-42", HTTP_X_CMS_INTERNAL="internal-test-secret")
    client.patch("/api/v1/hero-slides/18/", {"heading": "x", "expected_version": 1}, format="json")
    entry = AuditEntry.objects.get(resource="hero-slides", pk_value="18")
    assert entry.channel == "mcp" and entry.connector_session == "sess-42"


def test_in_process_mcp_context(content, editor):
    from apps.publishing import content as cms
    from apps.publishing.audit import WriteContext
    ctx = WriteContext(user=editor, channel="mcp", connector_session="claude-1")
    obj = cms.update_by_item_id("home.hero.hero-slides:18", {"heading": "Via Claude"}, ctx=ctx, expected_version=1)
    assert obj.version == 2
    e = AuditEntry.objects.get(resource="hero-slides")
    assert (e.channel, e.connector_session, e.item_id) == ("mcp", "claude-1", "home.hero.hero-slides:18")
    from apps.publishing.errors import CMSError
    with pytest.raises(CMSError) as exc:
        cms.update_by_item_id("home.hero.hero-slides:18", {"nonexistent": 1}, ctx=ctx, expected_version=2)
    assert exc.value.code == "CMS_VALIDATION"
    with pytest.raises(ValueError):
        WriteContext(channel="email")


def test_attach_media_checks_min_width(content, editor, media_root):
    from django.core.files.base import ContentFile

    from apps.publishing import content as cms
    from apps.publishing.audit import WriteContext
    from apps.publishing.errors import CMSError
    from apps.publishing.models import MediaAsset
    from tests.support.images import make_image_bytes
    small = MediaAsset(); small.file.save("small.jpg", ContentFile(make_image_bytes(1200, 600)))
    big = MediaAsset(); big.file.save("big.jpg", ContentFile(make_image_bytes(2400, 1350)))
    ctx = WriteContext(user=editor)
    with pytest.raises(CMSError) as exc:
        cms.attach_media("hero-slides", 18, "image", small.pk, ctx=ctx, expected_version=1)
    assert exc.value.code == "CMS_IMAGE_TOO_SMALL"
    obj = cms.attach_media("hero-slides", 18, "image", big.pk, ctx=ctx, expected_version=1)
    assert obj.image.name == big.file.name and obj.version == 2


def test_reorder_one_child_list(api_as, content):
    """The admin reorders one parent's photos at a time (addendum A9 body {order:[ids]})."""
    from apps.innovations.models import Innovation, InnovationImage
    parent, other = Innovation.objects.order_by("id")[:2]
    for n in range(3 - parent.images.count()):
        InnovationImage.objects.create(innovation=parent, image=f"innovation_images/p{n}.jpg", order=n)
    if not other.images.exists():
        InnovationImage.objects.create(innovation=other, image="innovation_images/o.jpg")
    ids = list(parent.images.order_by("order", "id").values_list("id", flat=True))
    client = api_as("editor")
    resp = client.post("/api/v1/innovation-images/reorder/", {"order": list(reversed(ids))}, format="json")
    assert resp.status_code == 200, resp.content
    assert list(parent.images.order_by("order", "id").values_list("id", flat=True)) == list(reversed(ids))
    others = InnovationImage.objects.exclude(innovation=parent).values_list("id", flat=True)
    if others:
        mixed = [ids[0], others[0]]
        assert_contract_error(client.post("/api/v1/innovation-images/reorder/", {"order": mixed}, format="json"),
                              "CMS_VALIDATION", field="order")
    assert_contract_error(client.post("/api/v1/innovation-images/reorder/", {"order": ids[:1]}, format="json"),
                          "CMS_VALIDATION", field="order")
