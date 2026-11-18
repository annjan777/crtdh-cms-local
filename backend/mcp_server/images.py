"""Image checks and re-encoding for photos that arrive through MCP.

TODO(integration, backend-security): call
`apps.common.images.process_upload(io.BytesIO(data), min_width=None, kind="image")` instead of
`_local_process`. It returns ProcessedImage(path=<temp file>, width, height, sha256, mime) —
read the bytes from `path`, ext from `.ext` — and raises CMSError(CMS_VALIDATION) on bad
input (map its `.body` to errors.CmsError). Both must:
check type by content (not extension), allow only JPEG/PNG/WebP, refuse SVG/HTML, cap
pixels, and re-encode (dropping EXIF and any appended payload).
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import CmsError

MAX_PIXELS = 40_000_000  # ~ 8000 x 5000
_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


@dataclass
class ProcessedImage:
    content: bytes
    ext: str
    width: int
    height: int
    sha256: str  # of the bytes we received, so the same photo de-duplicates


def _not_an_image() -> CmsError:
    return CmsError(
        "CMS_VALIDATION",
        "That file is not a JPEG, PNG or WebP photo (SVG, HTML and other formats are not accepted). Nothing was saved.",
        fix="Ask the user for the photo as a JPEG or PNG.",
        field="url",
    )


def _local_process(data: bytes) -> ProcessedImage:
    digest = hashlib.sha256(data).hexdigest()
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            if fmt not in _FORMATS:
                raise _not_an_image()
            if probe.width * probe.height > MAX_PIXELS:
                raise CmsError("CMS_VALIDATION", "That photo is too large in pixels to process.", field="url")
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
            out = io.BytesIO()
            if fmt == "JPEG":
                img.convert("RGB").save(out, "JPEG", quality=90, optimize=True)
            elif fmt == "PNG":
                img.save(out, "PNG", optimize=True)
            else:
                img.save(out, "WEBP", quality=90)
            return ProcessedImage(out.getvalue(), _FORMATS[fmt], img.width, img.height, digest)
    except CmsError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, SyntaxError):
        raise _not_an_image() from None


def process_image(data: bytes) -> ProcessedImage:
    return _local_process(data)
