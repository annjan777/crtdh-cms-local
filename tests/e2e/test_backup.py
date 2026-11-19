"""Download / upload backup against the real stack (owner decision 2026-11-20): Admin downloads a content backup
and a full one; an edit made afterwards is rolled back by uploading the content backup, as unpublished changes."""
import io
import json
import time
import zipfile

import pytest

from helpers import api_session

pytestmark = pytest.mark.needs_integration


def test_download_and_roll_back_with_a_backup(stack):
    admin = api_session(stack, "ada_admin")
    status, content_zip = admin("GET", "/api/v1/cms/backup/", raw=True)
    assert status == 200, content_zip[:200]
    zf = zipfile.ZipFile(io.BytesIO(content_zip))
    manifest = json.loads(zf.read("manifest.json"))
    assert set(zf.namelist()) == {"manifest.json", "snapshot.json"} and manifest["includes_media"] is False

    status, full_zip = admin("GET", "/api/v1/cms/backup/?photos=1", raw=True)
    assert status == 200
    full = zipfile.ZipFile(io.BytesIO(full_zip))
    photos = [n for n in full.namelist() if n.startswith("media/")]
    assert photos and json.loads(full.read("manifest.json"))["media_missing_on_server"] == []

    _, rows = admin("GET", "/api/v1/hero-slides/")
    rows = rows.get("results", rows) if isinstance(rows, dict) else rows
    slide = next(r for r in rows if r.get("is_published"))
    edited = f"Edited after backup {time.time():.0f}"
    status, _ = admin("PATCH", f"/api/v1/hero-slides/{slide['id']}/", {"heading": edited, "expected_version": slide["version"]})
    assert status == 200

    status, result = admin("POST", "/api/v1/cms/backup/restore/", files={"file": ("backup.zip", content_zip)})
    assert status == 200, result
    assert result["restored"] >= 1 and result["photos_written"] == 0
    _, after = admin("GET", f"/api/v1/hero-slides/{slide['id']}/")
    assert after["heading"] == slide["heading"]

    editor = api_session(stack, "erin_editor")
    status, _ = editor("GET", "/api/v1/cms/backup/", raw=True)
    assert status == 403
