"""In-memory image files for upload tests (min-width rules, polyglots, SVG rejection)."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def make_image_bytes(width=2400, height=1350, fmt="JPEG", color=(15, 76, 117)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format=fmt)
    return buf.getvalue()


def make_image_file(width=2400, height=1350, fmt="JPEG", name=None):
    ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
    content_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    return SimpleUploadedFile(name or f"test_{width}x{height}.{ext}", make_image_bytes(width, height, fmt), content_type=content_type)


def polyglot_jpeg_html():
    """Valid JPEG header with an HTML/script payload appended (stored-XSS probe)."""
    return make_image_bytes(1700, 1000) + b"<html><script>alert(1)</script></html>"


SVG_WITH_SCRIPT = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
