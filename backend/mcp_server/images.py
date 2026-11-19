"""Image checks and re-encoding for photos that arrive through MCP.

Delegates to backend-security's `apps.common.images.process_upload(data, kind="image")`, the
one upload checker for the whole CMS: type by content (not extension), JPEG/PNG/WebP only,
no SVG/HTML/polyglots, pixel cap, and a re-encode that drops EXIF and any appended payload.
It returns ProcessedImage(path=<temp file we own>, width, height, sha256, mime, .ext); the
adapter hands it to apps.publishing.uploads.save_media, which removes the temp file.
"""

from __future__ import annotations

from apps.common.errors import CMSError
from apps.common.images import process_upload

from .errors import CmsError


def process_image(data: bytes):
    try:
        return process_upload(data, min_width=None, kind="image")
    except CMSError as exc:
        body = exc.body
        code = body.get("code") if body.get("code") in ("CMS_VALIDATION", "CMS_IMAGE_TOO_SMALL") else "CMS_VALIDATION"
        raise CmsError(
            code,
            f"{body.get('message') or 'That file is not a usable photo.'} Nothing was saved.",
            fix="Ask the user for the photo as a JPEG or PNG, or use request_upload_link.",
            field="url",
        ) from None
