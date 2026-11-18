"""CMS endpoints: pages, page detail, preview, review requests, upload links, audit."""
import pytest

from apps.publishing.models import AuditEntry, MediaAsset, ReviewRequest
from tests.support.errors import assert_contract_error
from tests.support.images import SVG_WITH_SCRIPT, make_image_file, polyglot_jpeg_html

pytestmark = pytest.mark.django_db


def test_pages_list_with_has_changes(api_as, baseline):
    client = api_as("editor")
    pages = client.get("/api/v1/cms/pages/").json()["pages"]
    assert [p["id"] for p in pages][:3] == ["home", "about", "team"] and len(pages) == 12
    assert not any(p["has_changes"] for p in pages)
    member = client.get("/api/v1/team-members/").json()["results"][0]
    client.patch(f"/api/v1/team-members/{member['id']}/", {"name": "Prof. New", "expected_version": member["version"]},
                 format="json")
    pages = {p["id"]: p for p in client.get("/api/v1/cms/pages/").json()["pages"]}
    assert pages["team"]["has_changes"] and not pages["home"]["has_changes"]


def test_page_detail_has_values_and_versions(api_as, content, media_root):
    """Addendum A1: sections[i].items = [{item_id, pk, version, values, media, children}]."""
    from apps.carousel.models import HeroSlide

    from .conftest import image_file
    image_file(media_root / "hero_slides" / "a.jpg", 1800, 1000)
    HeroSlide.objects.filter(pk=18).update(image="hero_slides/a.jpg")
    page = api_as("editor").get("/api/v1/cms/pages/home/").json()
    hero = page["sections"][0]
    assert hero["id"] == "home.hero" and hero["fields"][0]["min_width"] == 1600
    assert hero["fields"][0]["position_field"] == "image_position"
    ids = [i["item_id"] for i in hero["items"]]
    assert "home.hero.hero-slides:9001" in ids  # hidden rows are editable
    item = next(i for i in hero["items"] if i["pk"] == 18)
    assert item["version"] == 1 and "heading" in item["values"] and "version" not in item["values"]
    assert item["media"]["image"] == {"width": 1800, "height": 1000, "name": "a.jpg"}
    objective = next(s for s in page["sections"] if s["id"] == "home.objective")
    assert len(objective["items"]) == 1
    only = objective["items"][0]
    assert only["item_id"] == "home.objective.home-page:1" and "objective_text" in only["values"]
    covid = api_as("editor").get("/api/v1/cms/pages/covid-19/").json()
    grids = next(s for s in covid["sections"] if s["id"] == "covid-19.photo-sections")
    assert grids["items"] and all(i["values"]["page"] == "covid-19" for i in grids["items"])
    photos = [c for i in grids["items"] for c in i["children"]["image-grid-items"]]
    assert photos and all(c["item_id"].startswith("covid-19.photo-sections.image-grid-items:") for c in photos)
    site = api_as("editor").get("/api/v1/cms/pages/site/").json()
    assert {s["id"] for s in site["sections"]} == {"site.nav", "site.social", "site.logos"}
    assert_contract_error(api_as("editor").get("/api/v1/cms/pages/nope/"), "CMS_NOT_FOUND")


def test_page_detail_children_per_parent(api_as, content):
    from apps.innovations.models import InnovationImage
    page = api_as("editor").get("/api/v1/cms/pages/innovations/").json()
    section = next(s for s in page["sections"] if s["id"] == "innovations.list")
    assert section["children"][0]["resource"] == "innovation-images"
    for item in section["items"]:
        kids = item["children"]["innovation-images"]
        expected = list(InnovationImage.objects.filter(innovation_id=item["pk"]).order_by("order", "id")
                        .values_list("id", flat=True))
        assert [k["pk"] for k in kids] == expected


def test_preview_is_snapshot_shaped_for_the_page(api_as, content):
    data = api_as("editor").get("/api/v1/cms/preview/home/").json()
    assert data["page"] == "home"
    assert {"hero-slides", "news-items", "nav-items", "team-members"} <= set(data["collections"])
    assert {"home-page", "site-settings"} <= set(data["singletons"])
    assert 9001 not in [r["id"] for r in data["collections"]["hero-slides"]]
    assert_contract_error(api_as("editor").get("/api/v1/cms/preview/nope/"), "CMS_NOT_FOUND")


def test_review_request_emails_publishers(api_as, content, publisher, cms_admin, mail_outbox, editor):
    resp = api_as(editor).post("/api/v1/cms/review-requests/", {"note": "Hero updated for the camp"}, format="json")
    assert resp.status_code == 201
    assert len(mail_outbox) == 1
    mail = mail_outbox[0]
    assert set(mail.to) == {publisher.email, cms_admin.email}
    assert "Hero updated for the camp" in mail.body and "Erin Editor" in mail.subject
    open_list = api_as("editor").get("/api/v1/cms/review-requests/").json()["open"]
    assert open_list[0]["requested_by"] == "erin_editor"
    assert ReviewRequest.objects.count() == 1


def test_upload_link_one_time(api_as, client, content, media_root):
    resp = api_as("editor").post("/api/v1/cms/upload-links/", {"min_width": 1600}, format="json")
    assert resp.status_code == 201
    link = resp.json()
    assert set(link) == {"url", "token", "expires_at"} and link["url"].endswith(f"/api/v1/cms/upload/{link['token']}/")
    path = f"/api/v1/cms/upload/{link['token']}/"
    page = client.get(path)
    assert page.status_code == 200 and b'type="file"' in page.content and b"<script" not in page.content
    small = client.post(path, {"file": make_image_file(1599, 900)}, HTTP_ACCEPT="application/json")
    assert_contract_error(small, "CMS_IMAGE_TOO_SMALL")
    svg = client.post(path, {"file": __import__("django.core.files.uploadedfile", fromlist=["x"]).SimpleUploadedFile(
        "x.svg", SVG_WITH_SCRIPT, content_type="image/svg+xml")}, HTTP_ACCEPT="application/json")
    assert_contract_error(svg, "CMS_VALIDATION")
    ok = client.post(path, {"file": make_image_file(2400, 1350)}, HTTP_ACCEPT="application/json")
    assert ok.status_code == 201
    media = MediaAsset.objects.get(pk=ok.json()["media_id"])
    assert (media.width, media.height) == (2400, 1350)
    again = client.post(path, {"file": make_image_file(2400, 1350)}, HTTP_ACCEPT="application/json")
    assert again.status_code == 404
    from apps.publishing.uploads import link_status
    assert link_status(link["token"])["media_id"] == media.pk


def test_upload_reencodes_polyglot(client, editor, content, media_root):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.publishing.uploads import create_upload_link
    link = create_upload_link(editor)
    resp = client.post(f"/api/v1/cms/upload/{link['token']}/",
                       {"file": SimpleUploadedFile("p.jpg", polyglot_jpeg_html(), content_type="image/jpeg")},
                       HTTP_ACCEPT="application/json")
    # apps.common.images (backend-security) rejects polyglots outright rather than re-encoding them.
    assert_contract_error(resp, "CMS_VALIDATION")
    assert not MediaAsset.objects.exists()
    from apps.publishing.uploads import link_status
    assert link_status(link["token"])["used"] is False


def test_upload_link_expired_or_unknown(client, editor, content, settings):
    from datetime import timedelta

    from django.utils import timezone

    from apps.publishing.models import UploadLink
    from apps.publishing.uploads import create_upload_link
    link = create_upload_link(editor)
    UploadLink.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert client.get(f"/api/v1/cms/upload/{link['token']}/").status_code == 404
    assert client.get("/api/v1/cms/upload/not-a-token/").status_code == 404


def test_audit_endpoint_filters_by_item(api_as, content):
    """Addendum A8: {entries:[{item_id, at, author, channel, action, fields}]}."""
    client = api_as("editor")
    client.patch("/api/v1/hero-slides/18/", {"heading": "A", "expected_version": 1}, format="json")
    client.patch("/api/v1/hero-slides/19/", {"heading": "B", "expected_version": 1}, format="json")
    v = client.get("/api/v1/home-page/").json()["version"]
    client.patch("/api/v1/home-page/", {"women_text_1": "W", "expected_version": v}, format="json")
    entries = client.get("/api/v1/cms/audit/", {"item_id": "home.hero.hero-slides:18"}).json()["entries"]
    assert len(entries) == 1
    e = entries[0]
    assert (e["item_id"], e["author"], e["channel"], e["action"]) == ("home.hero.hero-slides:18", "erin_editor",
                                                                      "admin", "changed")
    assert [f["name"] for f in e["fields"]] == ["heading"] and e["fields"][0]["after"] == "A"
    rural = client.get("/api/v1/cms/audit/", {"item_id": "home.rural.home-page:1"}).json()["entries"]
    assert [f["name"] for f in rural[0]["fields"]] == ["women_text_1"]
    assert client.get("/api/v1/cms/audit/", {"item_id": "home.objective.home-page:1"}).json()["entries"] == []
    assert AuditEntry.objects.count() == 3


def test_changes_carry_review_request(api_as, content, publisher, mail_outbox, editor):
    client = api_as(editor)
    assert client.get("/api/v1/cms/changes/").json()["review_request"] is None
    client.post("/api/v1/cms/review-requests/", {"note": "Please check the hero"}, format="json")
    rr = client.get("/api/v1/cms/changes/").json()["review_request"]
    assert rr["by"] == "Erin Editor" and rr["note"] == "Please check the hero" and rr["at"]


def test_api_create_starts_hidden_unless_set(api_as, content):
    """Addendum A3."""
    client = api_as("editor")
    hidden = client.post("/api/v1/news-items/", {"text": "Draft line", "order": 9}, format="json")
    assert hidden.status_code == 201 and hidden.json()["is_published"] is False
    shown = client.post("/api/v1/news-items/", {"text": "Shown line", "order": 9, "is_published": True}, format="json")
    assert shown.status_code == 201 and shown.json()["is_published"] is True


def test_admin_add_creates_empty_hidden_draft_then_requires_fields_to_show(api_as, content):
    """The admin's "Add" posts only the parent/page and is_published=false; showing it needs the required fields."""
    from apps.innovations.models import Innovation, InnovationImage
    client = api_as("editor")
    parent = Innovation.objects.order_by("id").first()
    last = InnovationImage.objects.filter(innovation=parent).order_by("-order").first()
    resp = client.post("/api/v1/innovation-images/", {"innovation": parent.pk, "is_published": False}, format="json")
    assert resp.status_code == 201, resp.content
    row = resp.json()
    assert row["is_published"] is False and row["order"] == (last.order + 1 if last else 0)
    show = client.patch(f"/api/v1/innovation-images/{row['id']}/", {"is_published": True, "expected_version": 1},
                        format="json")
    assert_contract_error(show, "CMS_VALIDATION", field="image")
    assert InnovationImage.objects.get(pk=row["id"]).is_published is False
    hero = client.post("/api/v1/hero-slides/", {"is_published": False}, format="json")
    assert hero.status_code == 201
    grid = client.post("/api/v1/image-grid-blocks/", {"page": "covid-19", "is_published": False}, format="json")
    assert grid.status_code == 201 and grid.json()["page"] == "covid-19"
