"""Opens a verified build tarball safely and describes what it contains."""
from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
import tarfile
from dataclasses import dataclass

from .cmsclient import BuildRejected

MAX_FILES = 50_000
MAX_TOTAL_BYTES = 4 * 1024 ** 3
# Contract addendum A13: /_media/<hash16>.<ext>, variants /_media/<hash16>-<width>.<fmt>
MEDIA_NAME = re.compile(r"^[0-9a-f]{16}(-\d+)?\.\w+$", re.ASCII)
MEDIA_PREFIX = "_media"  # web path of the shared, content-hashed media folder
# Every path segment must look like this on every OS the agent runs on (no ':' drive letters, no '\\').
SEGMENT = re.compile(r"^[A-Za-z0-9._@+~-]{1,200}$")
WINDOWS_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.I)


def _check_segment(seg: str, full: str) -> None:
    if (not SEGMENT.match(seg) or seg in (".", "..") or seg.endswith((".", " "))
            or WINDOWS_RESERVED.match(seg.split(".", 1)[0])):
        raise BuildRejected(f"unsafe path in build tarball: {full!r}")


@dataclass
class Bundle:
    root: str                      # local dir holding site/ and media/
    snapshot_id: str
    publish_id: str
    site_files: list               # [(relpath, size)] relpath uses "/"
    media_files: list              # [(name, size)]
    media_referenced: set | None   # every media name the snapshot uses; None = unknown (no GC)
    manifest: dict

    @property
    def site_dir(self) -> str:
        return os.path.join(self.root, "site")

    @property
    def media_dir(self) -> str:
        return os.path.join(self.root, "media")

    def local_site_path(self, rel: str) -> str:
        return os.path.join(self.site_dir, *rel.split("/"))

    def local_media_path(self, name: str) -> str:
        return os.path.join(self.media_dir, name)

    @property
    def site_bytes(self) -> int:
        return sum(s for _, s in self.site_files)


def _clean_name(name: str) -> str | None:
    while name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    if name in ("", "."):
        return None  # the archive root entry
    if name.startswith("/") or "\\" in name or "\x00" in name:
        raise BuildRejected(f"unsafe path in build tarball: {name!r}")
    norm = posixpath.normpath(name)
    if norm != name or norm.startswith("..") or "/../" in f"/{norm}/":
        raise BuildRejected(f"unsafe path in build tarball: {name!r}")
    for seg in norm.split("/"):
        _check_segment(seg, name)
    return norm


def _inside(dest_real: str, target: str) -> str:
    real = os.path.realpath(target)
    if os.path.commonpath([dest_real, real]) != dest_real:
        raise BuildRejected(f"unsafe path in build tarball: {target!r}")
    return real


def safe_id(value: str) -> str:
    """Snapshot ids become directory names; allow only a conservative character set."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", value)
    if not cleaned or cleaned.startswith(".") or len(cleaned) > 120:
        raise BuildRejected(f"snapshot id cannot be used as a folder name: {value!r}")
    return cleaned


def open_bundle(tar_path: str, dest: str, expect_snapshot: str, expect_publish: str) -> Bundle:
    try:
        return _open_bundle(tar_path, dest, expect_snapshot, expect_publish)
    except OSError as exc:  # e.g. site/x is a file and site/x/y follows, or the local disk is full
        raise BuildRejected(f"build tarball cannot be unpacked: {exc.__class__.__name__}: {exc.strerror or exc}") from None
    except (tarfile.TarError, EOFError, UnicodeError) as exc:
        raise BuildRejected(f"build tarball is damaged: {exc}") from None


def _open_bundle(tar_path: str, dest: str, expect_snapshot: str, expect_publish: str) -> Bundle:
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    dest_real = os.path.realpath(dest)
    total = 0
    count = 0
    try:
        tf = tarfile.open(tar_path, "r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise BuildRejected(f"build tarball cannot be opened: {exc}") from None
    with tf:
        for m in tf:
            name = _clean_name(m.name)
            if name is None:
                continue
            top = name.split("/", 1)[0]
            if top not in ("site", "media", "manifest.json"):
                raise BuildRejected(f"unexpected entry in build tarball: {name}")
            if m.isdir():
                d = _inside(dest_real, os.path.join(dest_real, *name.split("/")))
                os.makedirs(d, exist_ok=True)
                _inside(dest_real, d)  # re-check: nothing on the way may have become a link
                continue
            if not m.isfile():
                raise BuildRejected(f"build tarball may only contain files and folders: {name}")
            if top == "media" and (name.count("/") != 1 or not MEDIA_NAME.match(name.split("/")[1])):
                raise BuildRejected(f"bad media file name in build: {name}")
            if name.split("/")[:2] == ["site", MEDIA_PREFIX]:
                raise BuildRejected(f"site/{MEDIA_PREFIX}/ is reserved for the shared media folder")
            count += 1
            total += m.size
            if count > MAX_FILES or total > MAX_TOTAL_BYTES:
                raise BuildRejected("build tarball is too large")
            target = _inside(dest_real, os.path.join(dest_real, *name.split("/")))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            # Re-check after creating the parents: the final path must still resolve inside dest.
            target = _inside(dest_real, target)
            src = tf.extractfile(m)
            with src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)

    manifest_path = os.path.join(dest, "manifest.json")
    if not os.path.exists(manifest_path):
        raise BuildRejected("build tarball has no manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except ValueError:
        raise BuildRejected("manifest.json is not valid JSON") from None
    if str(manifest.get("snapshot_id", expect_snapshot)) != expect_snapshot:
        raise BuildRejected("manifest snapshot_id does not match the job")
    if str(manifest.get("publish_id", expect_publish)) != expect_publish:
        raise BuildRejected("manifest publish_id does not match the job")

    site_dir = os.path.join(dest, "site")
    if not os.path.isfile(os.path.join(site_dir, "index.html")):
        raise BuildRejected("build has no site/index.html")
    site_files = []
    for dirpath, _dirs, files in os.walk(site_dir):
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, site_dir).replace(os.sep, "/")
            site_files.append((rel, os.path.getsize(full)))
    site_files.sort()
    media_dir = os.path.join(dest, "media")
    media_files = sorted((f, os.path.getsize(os.path.join(media_dir, f)))
                         for f in (os.listdir(media_dir) if os.path.isdir(media_dir) else []))

    referenced = manifest.get("media")
    if isinstance(referenced, list) and all(isinstance(x, str) for x in referenced):
        ref_set = {posixpath.basename(x) for x in referenced}
        for name in ref_set:
            if not MEDIA_NAME.match(name):
                raise BuildRejected(f"bad media name in manifest: {name}")
    else:
        ref_set = None
    return Bundle(dest, expect_snapshot, expect_publish, site_files, media_files, ref_set, manifest)
