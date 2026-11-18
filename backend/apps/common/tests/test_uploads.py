import io
import struct
import zlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from PIL import Image
from rest_framework.serializers import ModelSerializer

from apps.common.errors import CMSError
from apps.common.fields import SafeFileField, SafeImageField
from apps.common.images import AVIF, make_variants, process_upload
from tests.support.images import SVG_WITH_SCRIPT, make_image_bytes, make_image_file, polyglot_jpeg_html

pytestmark = pytest.mark.security


def f(data, name="x.jpg", ctype="image/jpeg"):
    return SimpleUploadedFile(name, data, content_type=ctype)


def code_of(exc):
    return exc.value.body["code"]


def test_clean_jpeg_is_reencoded():
    out = process_upload(make_image_file(2400, 1350))
    assert (out.width, out.height, out.mime) == (2400, 1350, "image/jpeg") and len(out.sha256) == 64


def test_png_with_alpha_stays_png():
    buf = io.BytesIO()
    Image.new("RGBA", (500, 300), (0, 0, 0, 0)).save(buf, "PNG")
    assert process_upload(f(buf.getvalue(), "logo.png")).mime == "image/png"


def test_webp_accepted():
    assert process_upload(make_image_file(800, 600, "WEBP")).mime == "image/jpeg"


def test_exif_is_stripped():
    img = Image.new("RGB", (800, 600), "white")
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"  # Make
    exif[0x8825] = {2: (22.0, 19.0, 0.0)}  # GPS
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    assert b"SecretCam" in buf.getvalue()
    out = process_upload(f(buf.getvalue()))
    data = open(out.path, "rb").read()
    assert b"SecretCam" not in data and b"Exif" not in data
    assert not Image.open(out.path).getexif()


def test_exif_orientation_applied():
    img = Image.new("RGB", (1000, 600), "white")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    out = process_upload(f(buf.getvalue()))
    assert (out.width, out.height) == (600, 1000)


def test_polyglot_jpeg_html_rejected():
    with pytest.raises(CMSError) as e:
        process_upload(f(polyglot_jpeg_html()))
    assert code_of(e) == "CMS_VALIDATION"


def test_svg_rejected_even_named_jpg():
    with pytest.raises(CMSError):
        process_upload(f(SVG_WITH_SCRIPT, "photo.jpg"))
    with pytest.raises(CMSError):
        process_upload(f(SVG_WITH_SCRIPT, "x.svg", "image/svg+xml"))


def test_html_rejected():
    with pytest.raises(CMSError):
        process_upload(f(b"<!doctype html><html><script>x</script></html>", "a.png", "image/png"))


def test_gifar_style_zip_tail_rejected():
    with pytest.raises(CMSError):
        process_upload(f(make_image_bytes(600, 400) + b"PK\x03\x04junk" + b"PK\x05\x06" + b"\0" * 18))


def _png_header_only(w, h):
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\0" * 64)) + chunk(b"IEND", b"")


def test_decompression_bomb_rejected():
    with pytest.raises(CMSError) as e:
        process_upload(f(_png_header_only(30000, 30000), "bomb.png", "image/png"))
    assert "too large" in e.value.body["message"]


def test_truncated_image_rejected():
    with pytest.raises(CMSError):
        process_upload(f(make_image_bytes(800, 600)[:300]))


def test_size_cap(settings):
    settings.UPLOAD_LIMITS = dict(settings.UPLOAD_LIMITS, image=1000)
    with pytest.raises(CMSError) as e:
        process_upload(make_image_file(800, 600))
    assert "larger than" in e.value.body["message"]


def test_tiny_hero_rejected_with_contract_code():
    with pytest.raises(CMSError) as e:
        process_upload(make_image_file(1599, 900), min_width=1600)
    assert code_of(e) == "CMS_IMAGE_TOO_SMALL" and e.value.status_code == 400
    process_upload(make_image_file(1600, 900), min_width=1600)


def test_huge_image_capped_to_max_edge():
    out = process_upload(make_image_file(6000, 3000))
    assert max(out.width, out.height) == 4096


def test_pdf_accepted_and_script_pdf_rejected():
    ok = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF"
    assert process_upload(f(ok, "a.pdf", "application/pdf"), kind="document").mime == "application/pdf"
    bad = b"%PDF-1.4\n1 0 obj << /OpenAction << /S /JavaScript /JS (app.alert(1)) >> >> endobj"
    with pytest.raises(CMSError):
        process_upload(f(bad, "a.pdf", "application/pdf"), kind="document")
    with pytest.raises(CMSError):
        process_upload(f(make_image_bytes(100, 100), "a.pdf", "application/pdf"), kind="document")


def test_variants_widths_and_formats(tmp_path):
    out = process_upload(make_image_file(2000, 1000))
    v = make_variants(out.path, out_dir=str(tmp_path))
    first = "avif" if AVIF else "jpeg"
    assert set(v) == {first, "webp"}
    assert [x["width"] for x in v["webp"]] == [480, 960, 1600]
    for x in v[first] + v["webp"]:
        assert Image.open(x["path"]).width == x["width"]


def test_small_source_gets_single_variant(tmp_path):
    out = process_upload(make_image_file(300, 200))
    assert [x["width"] for x in make_variants(out.path, out_dir=str(tmp_path))["webp"]] == [300]


def test_every_model_serializer_file_field_is_safe():
    from django.apps import apps as django_apps
    assert ModelSerializer.serializer_field_mapping[models.ImageField] is SafeImageField
    assert ModelSerializer.serializer_field_mapping[models.FileField] is SafeFileField
    import importlib
    checked = 0
    for cfg in django_apps.get_app_configs():
        if not cfg.name.startswith("apps."):
            continue
        try:
            mod = importlib.import_module(cfg.name + ".serializers")
        except ModuleNotFoundError:
            continue
        for obj in vars(mod).values():
            if isinstance(obj, type) and issubclass(obj, ModelSerializer) and obj is not ModelSerializer:
                if getattr(getattr(obj, "Meta", None), "model", None) is None:
                    continue
                for name, field in obj().fields.items():
                    if field.read_only:
                        continue
                    if type(field).__name__ in ("ImageField", "FileField"):
                        raise AssertionError(f"{obj.__name__}.{name} bypasses upload checks")
                    if isinstance(field, (SafeImageField, SafeFileField)):
                        checked += 1
    assert checked >= 25


@pytest.mark.django_db
def test_hero_upload_through_api(api_as, media_root):
    c = api_as("superuser")  # hero-slides still use is_staff until backend-core's role permissions land
    small = c.post("/api/v1/hero-slides/", {"image": make_image_file(1200, 700), "title": "t"}, format="multipart")
    assert small.status_code == 400 and small.json()["code"] == "CMS_IMAGE_TOO_SMALL"
    assert small.json()["field"] == "image"
    poly = c.post("/api/v1/hero-slides/", {"image": f(polyglot_jpeg_html()), "title": "t"}, format="multipart")
    assert poly.status_code == 400 and poly.json()["code"] == "CMS_VALIDATION"
    ok = c.post("/api/v1/hero-slides/", {"image": make_image_file(2400, 1350, name="../../evil.jpg"), "title": "t"},
                format="multipart")
    assert ok.status_code == 201, ok.content
    assert "evil" not in ok.json()["image"] and ".." not in ok.json()["image"]


@pytest.mark.django_db
def test_media_requires_cms_session(api_as, media_root):
    (media_root / "a").mkdir()
    (media_root / "a" / "x.jpg").write_bytes(make_image_bytes(10, 10))
    from rest_framework.test import APIClient
    assert APIClient().get("/api/v1/media/a/x.jpg").status_code == 401
    r = api_as("editor").get("/api/v1/media/a/x.jpg")
    assert r.status_code == 200 and r["X-Content-Type-Options"] == "nosniff"
    assert api_as("editor").get("/api/v1/media/../settings.py").status_code == 404
