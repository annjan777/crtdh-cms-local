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
PDF_FORBIDDEN = re.compile(rb"/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|XFA|AA|SubmitForm|ImportData|GoToE)\b")
PDF_NAME = re.compile(rb"/(?:[^\s/<>\[\]()%{}#]|#[0-9A-Fa-f]{2})+")
PDF_HEX = re.compile(rb"#([0-9A-Fa-f]{2})")
PDF_INFLATE_BUDGET = 128 * 1024 * 1024  # max size of the fully decoded rewrite that is inspected

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


# Metadata containers that photo tools fill with XML, and that may legitimately hold markup: XMP, EXIF,
# comments, and C2PA "Content Credentials" (caBX in PNG, APP11/JUMBF in JPEG), which can embed an SVG icon.
# They are skipped by the markup scan below. That is safe because nothing from the original file is kept:
# the image is decoded and re-encoded from its pixels, which drops every metadata block. The pixel data
# and anything appended after the image's end marker are still scanned.
PNG_METADATA_CHUNKS = {b"caBX", b"iTXt", b"tEXt", b"zTXt", b"eXIf"}
JPEG_METADATA_MARKERS = {0xE1, 0xEB, 0xFE}  # APP1 (EXIF/XMP), APP11 (JUMBF/C2PA), COM


def _without_metadata(data, fmt):
    """`data` minus known metadata blocks, or `data` unchanged if the structure doesn't parse cleanly."""
    try:
        if fmt == "PNG":
            out, pos = bytearray(data[:8]), 8
            while pos + 12 <= len(data):
                length = int.from_bytes(data[pos:pos + 4], "big")
                kind = data[pos + 4:pos + 8]
                end = pos + 12 + length
                if end > len(data):
                    return data
                if kind not in PNG_METADATA_CHUNKS:
                    out += data[pos:end]
                pos = end
                if kind == b"IEND":
                    return bytes(out + data[pos:])  # bytes after IEND are kept and scanned
            return data
        if fmt == "JPEG":
            out, pos = bytearray(data[:2]), 2
            while pos + 4 <= len(data) and data[pos] == 0xFF:
                marker = data[pos + 1]
                if marker == 0xDA:  # start of scan: the rest is image data and trailer, all scanned
                    return bytes(out + data[pos:])
                length = int.from_bytes(data[pos + 2:pos + 4], "big")
                end = pos + 2 + length
                if length < 2 or end > len(data):
                    return data
                if marker not in JPEG_METADATA_MARKERS:
                    out += data[pos:end]
                pos = end
            return data
    except (IndexError, ValueError):
        return data
    return data


def _tmp(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="crtdh-upload-", dir=settings.FILE_UPLOAD_TEMP_DIR)
    os.close(fd)
    return path


def _process_image(data, min_width):
    fmt = sniff_image(data)
    if fmt is None:
        _reject("That file is not a JPEG, PNG or WebP image (SVG and HTML are not accepted).")
    scanned = _without_metadata(data, fmt)
    if POLYGLOT_MARKERS.search(scanned) or ZIP_EOCD in data[-70000:]:
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


def _pdf_normalise(chunk):
    """Decode #xx escapes inside PDF names (/J#61vaScript -> /JavaScript)."""
    return PDF_NAME.sub(lambda m: PDF_HEX.sub(lambda h: bytes([int(h.group(1), 16)]), m.group(0)), chunk)


PDF_ACTIVE_NAMES = {"/" + n for n in ("JavaScript", "JS", "Launch", "EmbeddedFile", "EmbeddedFiles", "RichMedia",
                                       "XFA", "AA", "SubmitForm", "ImportData", "GoToE", "Rendition", "Sound", "Movie")}
PDF_ALLOWED_FILTERS = {"/FlateDecode", "/DCTDecode", "/JPXDecode", "/CCITTFaxDecode", "/JBIG2Decode"}


class _BoundedSink(io.RawIOBase):
    """Write target that gives up past `limit` bytes (decompression-bomb guard for the rewrite)."""

    def __init__(self, limit):
        self.limit, self.buf = limit, bytearray()

    def writable(self):
        return True

    def write(self, b):
        if len(self.buf) + len(b) > self.limit:
            raise OverflowError("PDF expands past the inspection budget")
        self.buf += b
        return len(b)


def _pdf_walk(obj, depth=0):
    """True if a PDF object (dictionary/array, not following references) names active content."""
    import pikepdf

    if depth > 64:
        return True
    if isinstance(obj, pikepdf.Name):
        return str(obj) in PDF_ACTIVE_NAMES
    if isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)):
        for key in obj.keys():
            if key in PDF_ACTIVE_NAMES:
                return True
            val = obj.get(key)
            if key in ("/Filter", "/F") and isinstance(obj, pikepdf.Stream):
                names = [val] if isinstance(val, pikepdf.Name) else list(val) if isinstance(val, pikepdf.Array) else []
                if any(str(n) not in PDF_ALLOWED_FILTERS for n in names):
                    return True  # ASCIIHex/ASCII85/LZW/RunLength/Crypt: no legitimate need, hides content
            if not getattr(val, "is_indirect", False) and _pdf_walk(val, depth + 1):
                return True
        return False
    if isinstance(obj, pikepdf.Array):
        return any(not getattr(v, "is_indirect", False) and _pdf_walk(v, depth + 1) for v in obj)
    return False


def _pdf_is_active(data):
    """True if the PDF has (or may hide) scripts, actions or embedded files.

    Three layers: (1) the raw bytes, with #xx name escapes decoded; (2) qpdf (pikepdf) parses the
    document, including objects packed in object streams under any filter chain, and every object is
    walked for active-content names and non-image stream filters; (3) qpdf rewrites the whole file with
    object streams expanded and every stream fully decoded (bounded size) and that text is scanned.
    Encrypted, unparseable or oversized-when-decoded PDFs cannot be inspected and count as active."""
    import pikepdf

    if PDF_FORBIDDEN.search(_pdf_normalise(data)) or POLYGLOT_MARKERS.search(data):
        return True
    try:
        with pikepdf.open(io.BytesIO(data)) as pdf:
            if pdf.is_encrypted:
                return True
            for obj in pdf.objects:
                if _pdf_walk(obj):
                    return True
            sink = _BoundedSink(PDF_INFLATE_BUDGET)
            pdf.save(sink, compress_streams=False, stream_decode_level=pikepdf.StreamDecodeLevel.all,
                     object_stream_mode=pikepdf.ObjectStreamMode.disable, qdf=False)
    except (pikepdf.PasswordError, pikepdf.PdfError, OverflowError, ValueError, RecursionError):
        return True
    out = bytes(sink.buf)
    return bool(PDF_FORBIDDEN.search(_pdf_normalise(out)) or POLYGLOT_MARKERS.search(out))


def _process_document(data):
    if not data.startswith(b"%PDF-"):
        _reject("That file is not a PDF.", fix="Upload a PDF document.")
    if _pdf_is_active(data):
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
