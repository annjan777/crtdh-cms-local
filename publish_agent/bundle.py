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
MEDIA_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")


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
    return norm


def safe_id(value: str) -> str:
    """Snapshot ids become directory names; allow only a conservative character set."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", value)
    if not cleaned or cleaned.startswith(".") or len(cleaned) > 120:
        raise BuildRejected(f"snapshot id cannot be used as a folder name: {value!r}")
    return cleaned


def open_bundle(tar_path: str, dest: str, expect_snapshot: str, expect_publish: str) -> Bundle:
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
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
                os.makedirs(os.path.join(dest, *name.split("/")), exist_ok=True)
                continue
            if not m.isfile():
                raise BuildRejected(f"build tarball may only contain files and folders: {name}")
            if top == "media" and (name.count("/") != 1 or not MEDIA_NAME.match(name.split("/")[1])):
                raise BuildRejected(f"bad media file name in build: {name}")
            if name.startswith("site/media/") or name == "site/media":
                raise BuildRejected("site/media/ is reserved for the shared media folder")
            count += 1
            total += m.size
            if count > MAX_FILES or total > MAX_TOTAL_BYTES:
                raise BuildRejected("build tarball is too large")
            target = os.path.join(dest, *name.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
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
