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


def test_page_detail_has_values_and_versions(api_as, content):
    page = api_as("editor").get("/api/v1/cms/pages/home/").json()
    hero = page["sections"][0]
    assert hero["id"] == "home.hero" and hero["fields"][0]["min_width"] == 1600
    ids = [i["item_id"] for i in hero["items"]]
    assert "home.hero.hero-slides:9001" in ids  # hidden rows are editable
    item = hero["items"][0]
    assert item["version"] == 1 and "heading" in item["values"]
    objective = next(s for s in page["sections"] if s["id"] == "home.objective")
    assert objective["item_id"] == "home.objective.home-page:1" and set(objective["values"]) == {"objective_text"}
    covid = api_as("editor").get("/api/v1/cms/pages/covid-19/").json()
    grids = next(s for s in covid["sections"] if s["id"] == "covid-19.grids")
    assert all(i["values"]["page"] == "covid-19" for i in grids["items"])
    site = api_as("editor").get("/api/v1/cms/pages/site/").json()
    assert [s["id"] for s in site["sections"]][0] == "site.header"
    assert_contract_error(api_as("editor").get("/api/v1/cms/pages/nope/"), "CMS_NOT_FOUND")


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
    assert resp.status_code == 201
    stored = MediaAsset.objects.get(pk=resp.json()["media_id"]).file.read()
    assert b"<script" not in stored


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
    client = api_as("editor")
    client.patch("/api/v1/hero-slides/18/", {"heading": "A", "expected_version": 1}, format="json")
    client.patch("/api/v1/hero-slides/19/", {"heading": "B", "expected_version": 1}, format="json")
    v = client.get("/api/v1/home-page/").json()["version"]
    client.patch("/api/v1/home-page/", {"women_text_1": "W", "expected_version": v}, format="json")
    entries = client.get("/api/v1/cms/audit/", {"item_id": "home.hero.hero-slides:18"}).json()["results"]
    assert len(entries) == 1 and entries[0]["after"]["heading"] == "A" and entries[0]["actor"] == "erin_editor"
    assert client.get("/api/v1/cms/audit/", {"item_id": "home.women.home-page:1"}).json()["results"]
    assert client.get("/api/v1/cms/audit/", {"item_id": "home.objective.home-page:1"}).json()["results"] == []
    assert AuditEntry.objects.count() == 3
