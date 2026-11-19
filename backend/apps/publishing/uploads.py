"""One-time photo upload links (contract §3 POST /cms/upload-links/; MCP request_upload_link).

Image checking/re-encoding is backend-security's `apps.common.images.process_upload(file, min_width)`. Until that
lands, `_fallback_process_upload` below (same signature) does a minimal Pillow-based check and re-encode.
"""
import hashlib
import io
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .errors import CMSError
from .models import MediaAsset, UploadLink

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MAX_BYTES = 20 * 1024 * 1024


def _fallback_process_upload(file, min_width=0):
    """Return (ContentFile named <sha16>.<ext>, width, height). Raises CMSError."""
    from PIL import Image, UnidentifiedImageError

    data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise CMSError("CMS_VALIDATION", "The file is larger than 20 MB.", field="file")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        im = Image.open(io.BytesIO(data))
        fmt = im.format
        im.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise CMSError("CMS_VALIDATION", "That file is not a JPEG, PNG or WebP photo.", field="file") from None
    if fmt not in ALLOWED_FORMATS:
        raise CMSError("CMS_VALIDATION", "Only JPEG, PNG or WebP photos are accepted.", field="file")
    width, height = im.size
    if min_width and width < min_width:
        raise CMSError("CMS_IMAGE_TOO_SMALL", f"This photo is {width} px wide; it needs at least {min_width} px.",
                       field="file", fix=f"Upload a photo at least {min_width} px wide (see the shot list).")
    out = io.BytesIO()
    if fmt == "JPEG":
        im.convert("RGB").save(out, format="JPEG", quality=90)  # re-encode: drops EXIF and appended payloads
    else:
        im.save(out, format=fmt)
    body = out.getvalue()
    name = f"{hashlib.sha256(body).hexdigest()[:16]}.{ALLOWED_FORMATS[fmt]}"
    return ContentFile(body, name=name), width, height


def process_upload(file, min_width=0):
    try:
        from apps.common.images import process_upload as real  # backend-security
    except ImportError:
        return _fallback_process_upload(file, min_width)
    result = real(file, min_width or None, kind="image")
    if hasattr(result, "path") and hasattr(result, "sha256"):  # apps.common.images.ProcessedImage
        return processed_to_content(result), result.width, result.height
    if isinstance(result, tuple):
        return result
    if isinstance(result, dict):
        return result["file"], result.get("width"), result.get("height")
    return result, getattr(result, "width", None), getattr(result, "height", None)


def processed_to_content(processed):
    """apps.common.images.ProcessedImage -> ContentFile named <sha16>.<ext>; removes the temp file it owns."""
    try:
        with open(processed.path, "rb") as fh:
            body = fh.read()
    finally:
        Path(processed.path).unlink(missing_ok=True)
    return ContentFile(body, name=f"{processed.sha256[:16]}.{processed.ext}")


def save_media(processed, *, user):
    """Store an already-checked image (apps.common.images.ProcessedImage) as a MediaAsset owned by `user`.

    Used by the MCP adapter (upload_image_from_url). Re-encoding is deterministic, so the same photo gets the same
    <sha16>.<ext> name: an existing asset of the same user with that name is returned instead of a copy.
    Returns (asset, deduplicated).
    """
    content = processed_to_content(processed)
    existing = MediaAsset.objects.filter(uploaded_by=user, file=f"uploads/{content.name}").first()
    if existing is not None:
        return existing, True
    asset = MediaAsset(uploaded_by=user)
    asset.file.save(content.name, content, save=True)
    return asset, False


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_upload_link(user, *, ctx=None, min_width=0, request=None):
    token = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(minutes=settings.UPLOAD_LINK_TTL_MINUTES)
    UploadLink.objects.create(token_hash=_hash(token), created_by=user, min_width=min_width, expires_at=expires,
                              channel=getattr(ctx, "channel", "admin"),
                              connector_session=getattr(ctx, "connector_session", None))
    path = f"/api/v1/cms/upload/{token}/"
    url = request.build_absolute_uri(path) if request is not None else f"{settings.CMS_PUBLIC_URL.rstrip('/')}{path}"
    return {"url": url, "token": token, "expires_at": expires}


def get_link(token):
    link = UploadLink.objects.filter(token_hash=_hash(token or "")).select_related("media").first()
    if link is None or link.expires_at < timezone.now():
        return None
    return link


def link_status(token):
    link = UploadLink.objects.filter(token_hash=_hash(token or "")).select_related("media").first()
    if link is None:
        return None
    media = link.media
    return {"used": link.used_at is not None, "expired": link.expires_at < timezone.now(),
            "media_id": media.pk if media else None, "width": media.width if media else None,
            "height": media.height if media else None}


def consume(link, file):
    """Validate + store the upload, mark the link used. Returns the MediaAsset."""
    if link.used_at is not None:
        raise CMSError("CMS_VALIDATION", "This upload link has already been used.", fix="Ask for a new upload link.")
    content, _w, _h = process_upload(file, link.min_width)
    asset = MediaAsset(uploaded_by=link.created_by)
    asset.file.save(Path(content.name).name, content, save=True)
    claimed = UploadLink.objects.filter(pk=link.pk, used_at__isnull=True).update(used_at=timezone.now(), media=asset)
    if not claimed:
        asset.file.delete(save=False)
        asset.delete()
        raise CMSError("CMS_VALIDATION", "This upload link has already been used.", fix="Ask for a new upload link.")
    return asset
