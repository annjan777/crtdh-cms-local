"""Download / upload a CMS backup (owner decision 2026-11-20, replaces scheduled server backups).

A backup is a zip:
  manifest.json   format, version, snapshot schema version, created_at/by, sha256 of snapshot.json and of every
                  photo, whether photos are included
  snapshot.json   the CMS content as it is now (build_snapshot: every shown row, drafts included)
  media/<path>    (full backup only) each photo the content uses, at its MEDIA_ROOT path

Uploading one restores the content as *unpublished changes* (the same path as History -> Restore), so nothing
goes live until a Publisher publishes, and Review & publish can discard it. Photos are written only where
missing; an existing file is never overwritten. Everything in an uploaded file is checked before anything changes.
"""
import hashlib
import tempfile
import json
import os
import zipfile
from types import SimpleNamespace

from django.conf import settings
from django.utils import timezone

from . import changes
from .errors import CMSError
from .snapshot import SCHEMA_VERSION, build_snapshot, safe_media_path, validate

FORMAT = "crtdh-cms-backup"
VERSION = 1
# Photos and documents the CMS stores; anything else in an uploaded backup is refused.
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".pdf", ".mp4", ".webm"}
MAX_UNCOMPRESSED = int(getattr(settings, "BACKUP_MAX_BYTES", 2 * 1024**3))  # zip-bomb guard
MAX_ENTRIES = 20_000


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sources(snap):
    return sorted({entry["source"] for entry in (snap.get("media") or {}).values() if entry.get("source")})


def write_backup(fileobj, *, user, include_media):
    """Write a backup zip to `fileobj`; returns the manifest."""
    snap = build_snapshot(published_by=user)
    snap_bytes = json.dumps(snap, ensure_ascii=False, sort_keys=True, indent=1).encode()
    media = {}
    missing = []
    with zipfile.ZipFile(fileobj, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if include_media:
            for source in _sources(snap):
                path = safe_media_path(source)
                if path is None or not path.is_file():
                    missing.append(source)
                    continue
                media[source] = _file_sha256(path)
                zf.write(path, f"media/{source}", compress_type=zipfile.ZIP_STORED)  # photos are compressed already
        zf.writestr("snapshot.json", snap_bytes)
        manifest = {
            "format": FORMAT,
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": timezone.now().isoformat(),
            "created_by": getattr(user, "username", None),
            "snapshot_sha256": _sha256(snap_bytes),
            "includes_media": bool(include_media),
            "media_sha256": media,
            "media_missing_on_server": missing,
            "counts": {k: len(v) for k, v in (snap.get("collections") or {}).items()},
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=1))
    return manifest


def _bad(message, fix="Download a new backup from this CMS and upload that file.", field="file"):
    raise CMSError("CMS_VALIDATION", message, fix=fix, field=field)


def read_backup(fileobj):
    """Open and fully check an uploaded backup. Returns (manifest, snapshot, zipfile). Raises CMSError."""
    try:
        zf = zipfile.ZipFile(fileobj)
    except (zipfile.BadZipFile, OSError):
        _bad("This file is not a CRTDH backup (it is not a zip file).")
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
        _bad("This backup is too large to restore here.")
    for info in infos:
        name = info.filename
        is_link = (info.external_attr >> 16) & 0o170000 == 0o120000
        if is_link or name.startswith("/") or "\\" in name or ".." in name.split("/"):
            _bad("This backup contains a file with an unsafe name.")
        if info.is_dir():
            continue
        if name not in ("manifest.json", "snapshot.json") and not name.startswith("media/"):
            _bad(f"This backup contains an unexpected file ({name[:80]}).")
    try:
        manifest = json.loads(zf.read("manifest.json"))
        snap_bytes = zf.read("snapshot.json")
    except (KeyError, ValueError):
        _bad("This backup is missing its manifest or content.")
    if manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
        _bad("This file is not a CRTDH backup, or it comes from a newer CMS version.")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _bad("This backup was made by a different version of the CMS and can't be restored here.")
    if _sha256(snap_bytes) != manifest.get("snapshot_sha256"):
        _bad("This backup is damaged or was changed after it was downloaded (content checksum does not match).")
    try:
        snap = json.loads(snap_bytes)
    except ValueError:
        _bad("This backup's content can't be read.")
    errors = validate(snap)
    if errors:
        _bad(f"This backup's content is not valid ({errors[0][:120]}).")
    for source in _sources(snap):
        if safe_media_path(source) is None:
            _bad("This backup points at a photo outside the media folder.")
    media_entries = {i.filename[len("media/"):]: i for i in infos if i.filename.startswith("media/") and not i.is_dir()}
    expected = manifest.get("media_sha256") or {}
    if set(media_entries) != set(expected):
        _bad("This backup's photo list does not match its manifest.")
    for source in media_entries:
        if os.path.splitext(source)[1].lower() not in MEDIA_EXTENSIONS:
            _bad(f"This backup contains a file type the CMS does not store ({source[-40:]}).")
        if safe_media_path(source) is None:
            _bad("This backup contains a photo path outside the media folder.")
    return manifest, snap, zf, media_entries


def restore_backup(fileobj, *, ctx):
    """Check, write missing photos, then restore the content as unpublished changes."""
    manifest, snap, zf, media_entries = read_backup(fileobj)
    expected = manifest.get("media_sha256") or {}
    # Photos first: each is checked against the manifest and written beside its final name; only when every one
    # is good are they moved into place. A file the server already has is never overwritten.
    written, kept, staged = 0, 0, []
    try:
        for source, info in media_entries.items():
            path = safe_media_path(source)
            if path.exists():
                kept += 1
                continue
            data = zf.read(info)
            if _sha256(data) != expected[source]:
                _bad(f"A photo in this backup is damaged ({source[-40:]}).")
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".restoring")
            tmp.write_bytes(data)
            staged.append((tmp, path))
    except BaseException:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)
        raise
    for tmp, path in staged:
        os.replace(tmp, path)
        written += 1
    missing = [s for s in _sources(snap) if not safe_media_path(s).exists()]
    if missing:
        _bad(f"{len(missing)} photo(s) this backup needs are not on the server ({missing[0][-40:]} …).",
             fix="Upload the full backup (content + photos) instead.")
    restored = changes.restore_snapshot(SimpleNamespace(data=snap), ctx=ctx)
    return {"restored": restored, "photos_written": written, "photos_already_present": kept,
            "backup_created_at": manifest.get("created_at"), "includes_media": manifest.get("includes_media")}


def backup_filename(include_media):
    stamp = timezone.now().strftime("%Y-%m-%d-%H%M")
    return f"crtdh-backup-{stamp}{'-with-photos' if include_media else '-content'}.zip"


def build_file(*, user, include_media):
    """The backup in a temporary file (photos can be hundreds of MB, so not in memory)."""
    fh = tempfile.TemporaryFile()
    write_backup(fh, user=user, include_media=include_media)
    fh.seek(0)
    return fh
