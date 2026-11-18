"""Upload safety: sniff, bound, re-encode (WS5.3).

process_upload(file, min_width=None, kind="image") -> ProcessedImage
    `file`: bytes, a file-like object (read/seek) or a filesystem path.
    kind="image": JPEG/PNG/WebP (AVIF too if Pillow has it) by magic bytes only.
        Rejects SVG, HTML, polyglots, decompression bombs and oversize files,
        applies EXIF orientation, then re-encodes from pixels (drops EXIF, ICC,
        comments and any trailing payload). Output: JPEG q90, or PNG if the
        source has transparency. Long edge capped at MAX_EDGE.
    kind="document": PDF by magic bytes, no JavaScript/launch/embedded files.
    kind="video": MP4/WebM by magic bytes.
    Returns a temp file the caller owns (path) plus width/height/sha256/mime.

make_variants(path, out_dir=None) -> {"avif": [...], "webp": [...]}  (or {"webp", "jpeg"}
    when this Pillow has no AVIF codec). Each entry is {"width", "path"}; widths
    480/960/1600/2400, never upscaled.

Errors are CMSError with contract codes (CMS_VALIDATION, CMS_IMAGE_TOO_SMALL).
"""
import hashlib
import io
import os
import re
import tempfile
import warnings
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, ImageOps, features

from .errors import CMSError

VARIANT_WIDTHS = (480, 960, 1600, 2400)
MAX_EDGE = 4096
AVIF = features.check("avif")

IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
)
# Markers that must never appear anywhere in an image or document upload.
# Patterns are long enough that random compressed pixel data essentially never matches.
POLYGLOT_MARKERS = re.compile(
    rb"<(script|html|svg|iframe|object|embed|body|!doctype)[\s>/]|<\?php|javascript:",
    re.IGNORECASE,
)
ZIP_EOCD = b"PK\x05\x06"  # end of a ZIP central directory (GIFAR/JAR-style polyglots)
MP4_BRANDS = {b"isom", b"iso2", b"iso4", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1", b"M4V ", b"dash"}
PDF_FORBIDDEN = re.compile(rb"/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|XFA|AA)\b")

Image.MAX_IMAGE_PIXELS = settings.IMAGE_MAX_PIXELS


@dataclass
class ProcessedImage:
    path: str
    width: int | None
    height: int | None
    sha256: str
    mime: str

    @property
    def ext(self):
        return {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf",
                "video/mp4": "mp4", "video/webm": "webm"}[self.mime]


def _reject(message, fix="Upload a JPEG, PNG or WebP photo.", field=None):
    raise CMSError("CMS_VALIDATION", message, fix=fix, field=field)


def _read(file, limit):
    if isinstance(file, (bytes, bytearray)):
        file = io.BytesIO(file)
    if hasattr(file, "seek"):
        file.seek(0)
    data = file.read(limit + 1) if hasattr(file, "read") else open(file, "rb").read(limit + 1)
    if len(data) > limit:
        _reject(f"File is larger than {limit // (1024 * 1024)} MB.", fix="Upload a smaller file.")
    if not data:
        _reject("File is empty.")
    return data


def sniff_image(data):
    for sig, fmt in IMAGE_SIGNATURES:
        if data.startswith(sig):
            return fmt
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    if AVIF and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "AVIF"
    return None


def _tmp(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="crtdh-upload-", dir=settings.FILE_UPLOAD_TEMP_DIR)
    os.close(fd)
    return path


def _process_image(data, min_width):
    fmt = sniff_image(data)
    if fmt is None:
        _reject("That file is not a JPEG, PNG or WebP image (SVG and HTML are not accepted).")
    if POLYGLOT_MARKERS.search(data) or ZIP_EOCD in data[-70000:]:
        _reject("The image contains embedded markup or an archive and was rejected.",
                fix="Re-export the photo from your camera or editor and upload that.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(data))
            if img.format != fmt:
                _reject("The file's contents do not match its image type.")
            w, h = img.size
            if w * h > settings.IMAGE_MAX_PIXELS:
                _reject("Image dimensions are too large.", fix="Resize to under 8000 px on the long edge.")
            img.load()
    except CMSError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        _reject("Image dimensions are too large.", fix="Resize to under 8000 px on the long edge.")
    except Exception:
        _reject("The image could not be read; it may be damaged.")

    img = ImageOps.exif_transpose(img)
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
    width = img.size[0]
    if min_width and width < min_width:
        raise CMSError(
            "CMS_IMAGE_TOO_SMALL",
            f"This photo is {width} px wide; this section needs at least {min_width} px.",
            fix="Upload the original photo (2400 px or wider is best). See the shot list in the CMS help.",
        )
    if max(img.size) > MAX_EDGE:
        img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    # Build a fresh image from pixels only: nothing from the source container survives.
    if has_alpha:
        clean = Image.new("RGBA", img.size)
        clean.paste(img.convert("RGBA"))
        path, mime = _tmp(".png"), "image/png"
        clean.save(path, "PNG", optimize=True)
    else:
        clean = Image.new("RGB", img.size)
        clean.paste(img.convert("RGB"))
        path, mime = _tmp(".jpg"), "image/jpeg"
        clean.save(path, "JPEG", quality=90, optimize=True, progressive=True)
    return path, clean.size, mime


def _process_document(data):
    if not data.startswith(b"%PDF-"):
        _reject("That file is not a PDF.", fix="Upload a PDF document.")
    if PDF_FORBIDDEN.search(data) or POLYGLOT_MARKERS.search(data):
        _reject("The PDF contains scripts, actions or embedded files and was rejected.",
                fix="Print it to a new PDF (File > Print > Save as PDF) and upload that.")
    path = _tmp(".pdf")
    with open(path, "wb") as fh:
        fh.write(data)
    return path, (None, None), "application/pdf"


def _process_video(data):
    if data[4:8] == b"ftyp" and data[8:12] in MP4_BRANDS:
        mime, suffix = "video/mp4", ".mp4"
    elif data.startswith(b"\x1a\x45\xdf\xa3"):
        mime, suffix = "video/webm", ".webm"
    else:
        _reject("That file is not an MP4 or WebM video.", fix="Upload MP4 (H.264) or WebM.")
    path = _tmp(suffix)
    with open(path, "wb") as fh:
        fh.write(data)
    return path, (None, None), mime


def process_upload(file, min_width=None, kind="image"):
    limit = settings.UPLOAD_LIMITS[kind]
    data = _read(file, limit)
    if kind == "image":
        path, (w, h), mime = _process_image(data, min_width)
    elif kind == "document":
        path, (w, h), mime = _process_document(data)
    elif kind == "video":
        path, (w, h), mime = _process_video(data)
    else:
        raise ValueError(f"unknown upload kind {kind!r}")
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return ProcessedImage(path=path, width=w, height=h, sha256=digest, mime=mime)


def make_variants(path, out_dir=None):
    """Responsive variants of an already-processed image."""
    out_dir = out_dir or os.path.dirname(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    formats = [("avif", "AVIF", {"quality": 60})] if AVIF else [("jpeg", "JPEG", {"quality": 82, "progressive": True})]
    formats.append(("webp", "WEBP", {"quality": 80, "method": 6}))
    result = {name: [] for name, _, _ in formats}
    with Image.open(path) as src:
        src.load()
        widths = [w for w in VARIANT_WIDTHS if w <= src.width] or [src.width]
        for w in widths:
            h = round(src.height * w / src.width)
            resized = src.resize((w, h), Image.LANCZOS)
            for name, pil_fmt, opts in formats:
                img = resized.convert("RGB") if pil_fmt == "JPEG" else resized
                out = os.path.join(out_dir, f"{stem}-{w}.{'jpg' if name == 'jpeg' else name}")
                img.save(out, pil_fmt, **opts)
                result[name].append({"width": w, "path": out})
    return result
