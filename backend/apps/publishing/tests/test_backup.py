"""Download / upload backup (owner decision 2026-11-20): Admin only; restores as unpublished changes; every check
happens before anything changes; photos are written only where missing, never overwritten."""
import io
import json
import zipfile

import pytest

from apps.carousel.models import HeroSlide
from apps.facilities.models import Equipment
from tests.support.errors import assert_contract_error

from .conftest import image_file

pytestmark = pytest.mark.django_db


@pytest.fixture
def with_photo(content, media_root):
    image_file(media_root / "equipment" / "kept.jpg", 800, 600)
    row = Equipment.objects.order_by("pk").first()
    Equipment.objects.filter(pk=row.pk).update(image="equipment/kept.jpg")
    return media_root / "equipment" / "kept.jpg", row.pk


def download(client, photos):
    resp = client.get(f"/api/v1/cms/backup/{'?photos=1' if photos else ''}")
    assert resp.status_code == 200, resp.content[:300]
    assert resp["Content-Type"] == "application/zip" and "attachment" in resp["Content-Disposition"]
    return b"".join(resp.streaming_content)


def upload(client, data, name="crtdh-backup.zip"):
    f = io.BytesIO(data)
    f.name = name
    return client.post("/api/v1/cms/backup/restore/", {"file": f}, format="multipart")


def rezip(data, edit):
    """Copy a backup zip, letting `edit(name, bytes)` change or drop (None) entries, and add extras it returns."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            body = edit(info.filename, src.read(info))
            if body is not None:
                dst.writestr(info.filename, body)
    return out.getvalue()


@pytest.mark.parametrize("role", ["editor", "publisher"])
def test_only_admins_can_download_or_upload(api_as, content, role):
    client = api_as(role)
    assert client.get("/api/v1/cms/backup/").status_code == 403
    assert upload(client, b"x").status_code == 403


def test_anonymous_refused(api_as, content):
    assert api_as(None).get("/api/v1/cms/backup/").status_code in (401, 403)


def test_content_only_backup_has_manifest_and_content_but_no_photos(api_as, with_photo):
    data = download(api_as("admin"), photos=False)
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = set(zf.namelist())
    assert names == {"manifest.json", "snapshot.json"}
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["format"] == "crtdh-cms-backup" and manifest["includes_media"] is False
    assert manifest["counts"]["equipment"] >= 1


def test_full_backup_contains_each_photo(api_as, with_photo):
    data = download(api_as("admin"), photos=True)
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert "media/equipment/kept.jpg" in zf.namelist()
    assert zf.read("media/equipment/kept.jpg") == with_photo[0].read_bytes()


def test_upload_restores_as_unpublished_changes(api_as, with_photo):
    admin = api_as("admin")
    before = HeroSlide.objects.order_by("pk").first()
    data = download(admin, photos=False)
    HeroSlide.objects.filter(pk=before.pk).update(heading="Edited after the backup")
    resp = upload(admin, data)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["restored"] >= 1 and body["pending"] >= 1  # not live until a Publisher publishes
    assert HeroSlide.objects.get(pk=before.pk).heading == before.heading


def test_full_backup_brings_back_a_lost_photo(api_as, with_photo):
    path, pk = with_photo
    admin = api_as("admin")
    data = download(admin, photos=True)
    original = path.read_bytes()
    path.unlink()
    resp = upload(admin, data)
    assert resp.status_code == 200, resp.content
    assert resp.json()["photos_written"] == 1 and path.read_bytes() == original


def test_existing_photo_is_never_overwritten(api_as, with_photo):
    path, _ = with_photo
    admin = api_as("admin")
    data = download(admin, photos=True)
    path.write_bytes(b"changed on the server since")
    resp = upload(admin, data)
    assert resp.status_code == 200 and resp.json()["photos_already_present"] == 1
    assert path.read_bytes() == b"changed on the server since"


def test_content_only_upload_refused_when_photos_are_missing(api_as, with_photo):
    path, pk = with_photo
    admin = api_as("admin")
    data = download(admin, photos=False)
    path.unlink()
    HeroSlide.objects.update(heading="Untouched")
    resp = upload(admin, data)
    assert_contract_error(resp, "CMS_VALIDATION")
    assert "content + photos" in resp.json()["fix"]
    assert set(HeroSlide.objects.values_list("heading", flat=True)) == {"Untouched"}  # nothing changed


def test_tampered_content_is_refused_and_nothing_changes(api_as, with_photo):
    admin = api_as("admin")
    data = download(admin, photos=False)
    bad = rezip(data, lambda n, b: b.replace(b'"heading"', b'"heading" ') if n == "snapshot.json" else b)
    HeroSlide.objects.update(heading="Untouched")
    resp = upload(admin, bad)
    assert_contract_error(resp, "CMS_VALIDATION")
    assert "checksum" in resp.json()["message"]
    assert set(HeroSlide.objects.values_list("heading", flat=True)) == {"Untouched"}


def test_damaged_photo_is_refused_and_not_written(api_as, with_photo):
    path, _ = with_photo
    admin = api_as("admin")
    data = download(admin, photos=True)
    path.unlink()
    bad = rezip(data, lambda n, b: b + b"x" if n.startswith("media/") else b)
    resp = upload(admin, bad)
    assert_contract_error(resp, "CMS_VALIDATION")
    assert not path.exists() and not list(path.parent.glob("*.restoring"))


@pytest.mark.parametrize("name", ["../evil.jpg", "media/../../evil.jpg", "/etc/passwd", "extra.txt", "media/x.php"])
def test_unsafe_or_unexpected_entries_are_refused(api_as, with_photo, name):
    admin = api_as("admin")
    data = download(admin, photos=False)
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info))
        dst.writestr(name, b"x")
    assert_contract_error(upload(admin, out.getvalue()), "CMS_VALIDATION")


def test_not_a_zip_is_refused(api_as, content):
    resp = upload(api_as("admin"), b"definitely not a zip")
    assert_contract_error(resp, "CMS_VALIDATION")
    assert "not a CRTDH backup" in resp.json()["message"]


def test_no_file_is_refused(api_as, content):
    resp = api_as("admin").post("/api/v1/cms/backup/restore/", {}, format="multipart")
    assert_contract_error(resp, "CMS_VALIDATION")
