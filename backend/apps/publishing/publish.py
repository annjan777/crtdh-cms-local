"""Publish orchestration (plan WS1.7, contract §3/§5).

start_publish()  - request time: snapshot the CMS *now*, run the build guard, queue a Publish (single-flight).
run_once()       - worker: claim a queued (or stale building) publish and build it:
                   guard -> snapshot.json -> content-hashed media -> frontend build -> deterministic tarball
                   -> ready_for_upload (the publish agent takes it from there).
Every step is idempotent, so a crashed build is simply rebuilt (same snapshot -> identical tarball bytes).
"""
import gzip
import hashlib
import io
import json
import logging
import os
import shlex
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from . import guard
from .errors import CMSError
from .models import Publish, Snapshot
from .snapshot import (
    _file_info,
    avif_supported,
    build_snapshot,
    canonical_json,
)

log = logging.getLogger(__name__)
STALE_BUILD_AFTER = timedelta(minutes=30)


def publish_root():
    root = Path(settings.PUBLISH_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def media_store():
    path = publish_root() / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def active_publish():
    return Publish.objects.filter(status__in=Publish.ACTIVE).order_by("created_at").first()


def _running_error(p):
    return CMSError("CMS_PUBLISH_RUNNING", f"A publish is already running (id {p.id}, status {p.status}).",
                    fix="Wait for it to finish (GET /api/v1/cms/publish/<id>/), then publish again.", retryable=True)


def last_live_snapshot(exclude_id=None):
    qs = Snapshot.objects.filter(published_at__isnull=False)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.order_by("-published_at", "-id").first()


def start_publish(user, confirm_shrink=False):
    running = active_publish()
    if running:
        raise _running_error(running)
    data = build_snapshot(published_by=user)
    prev = last_live_snapshot()
    guard.check(data, prev.data if prev else None, confirm_shrink=confirm_shrink)
    digest = hashlib.sha256(canonical_json(data).encode()).hexdigest()
    try:
        with transaction.atomic():
            snap, _ = Snapshot.objects.get_or_create(snapshot_id=data["snapshot_id"],
                                                     defaults={"data": data, "sha256": digest, "created_by": user})
            return Publish.objects.create(snapshot=snap, created_by=user, confirm_shrink=confirm_shrink,
                                          step="queued", message="Waiting for the build worker.")
    except IntegrityError:
        running = active_publish()
        if running:
            raise _running_error(running) from None
        raise


def cancel_publish(p):
    if p.status not in (Publish.QUEUED, Publish.READY):
        raise CMSError("CMS_VALIDATION", f"A publish that is {p.status} cannot be cancelled.")
    Publish.objects.filter(pk=p.pk, status=p.status).update(status=Publish.CANCELLED, message="Cancelled; the live site is unchanged.",
                                                            updated_at=timezone.now())
    p.refresh_from_db()
    return p


# ---- worker -----------------------------------------------------------------------------------------------------
def claim_next():
    now = timezone.now()
    candidates = Publish.objects.filter(Q(status=Publish.QUEUED) |
                                        Q(status=Publish.BUILDING, updated_at__lt=now - STALE_BUILD_AFTER))
    for p in candidates.order_by("created_at"):
        claimed = Publish.objects.filter(pk=p.pk, status=p.status, updated_at=p.updated_at).update(
            status=Publish.BUILDING, step="guard", message="Building.", attempts=F("attempts") + 1,
            started_at=now, updated_at=now)
        if claimed:
            p.refresh_from_db()
            return p
    return None


def _set(p, **kw):
    kw["updated_at"] = timezone.now()
    Publish.objects.filter(pk=p.pk).update(**kw)
    for k, v in kw.items():
        setattr(p, k, v)


def run_once():
    """Build one publish if there is one. Returns it (or None)."""
    p = claim_next()
    if p is None:
        return None
    try:
        build(p)
    except Exception as e:
        message = e.body["message"] if isinstance(e, CMSError) else str(e)
        log.exception("publish %s failed at %s", p.id, p.step)
        _set(p, status=Publish.FAILED, message=f"Build failed at {p.step}: {message[:1500]} The live site is unchanged.")
    return p


def build(p):
    snap = p.snapshot
    data = snap.data
    _set(p, step="guard")
    prev = last_live_snapshot(exclude_id=snap.pk)
    guard.check(data, prev.data if prev else None, confirm_shrink=p.confirm_shrink)

    _set(p, step="snapshot")
    build_dir = publish_root() / "builds" / str(p.id)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    snapshot_path = build_dir / "snapshot.json"
    snapshot_path.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _set(p, snapshot_path=str(snapshot_path))

    _set(p, step="media")
    files = materialize_media(data, media_store())

    _set(p, step="frontend")
    out_dir = Path(settings.FRONTEND_BUILD_OUTPUT)
    run_frontend_build(snapshot_path, out_dir, build_dir / "build.log")

    _set(p, step="pack")
    # Only media that an earlier publish actually uploaded can be skipped (a baseline snapshot was never uploaded).
    uploaded = (Snapshot.objects.filter(publishes__status=Publish.LIVE).exclude(pk=snap.pk)
                .order_by("-published_at", "-id").first())
    prev_files = set(_media_files(uploaded.data)) if uploaded else set()
    tar_path = publish_root() / "tarballs" / f"crtdh-site-{data['snapshot_id']}.tar.gz"
    sha = pack_tarball(tar_path, site_dir=out_dir, media_dir=media_store(), media_all=files,
                       media_new=[f for f in files if f not in prev_files], snapshot_id=data["snapshot_id"],
                       publish_id=str(p.id), mtime=_epoch(data["published_at"]))
    _set(p, status=Publish.READY, step="waiting for upload machine", tarball_path=str(tar_path), tarball_sha256=sha,
         message="Built. Waiting for the upload machine to pick it up.")


def _epoch(published_at):
    return int(datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())


def _media_files(data):
    """File names (in the media store) the snapshot references: originals + variants."""
    out = []
    for key, entry in (data.get("media") or {}).items():
        out.append(key.rsplit("/", 1)[1])
        for variants in entry["variants"].values():
            out.extend(v["url"].rsplit("/", 1)[1] for v in variants)
    return sorted(set(out))


def _atomic_write(dst, writer):
    tmp = dst.with_name(f".{dst.name}.tmp{os.getpid()}")
    try:
        writer(tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def materialize_media(data, store):
    """Copy originals into the content-addressed store and render missing variants. Returns all file names."""
    from PIL import Image

    media_root = Path(settings.MEDIA_ROOT)
    for key, entry in (data.get("media") or {}).items():
        src = media_root / entry["source"]
        name = key.rsplit("/", 1)[1]
        dst = store / name
        if not dst.exists():
            if not src.is_file():
                raise CMSError("CMS_BUILD_GUARD", f"Media file {entry['source']} is missing; publish again.")
            sha = _file_info(src)[0]
            if not name.startswith(sha[:16]):
                raise CMSError("CMS_BUILD_GUARD", f"Media file {entry['source']} changed after the snapshot; publish again.")
            _atomic_write(dst, lambda tmp: shutil.copyfile(src, tmp))
        for fmt, variants in entry["variants"].items():
            if fmt == "avif" and not avif_supported():
                continue
            for v in variants:
                vdst = store / v["url"].rsplit("/", 1)[1]
                if vdst.exists():
                    continue

                def render(tmp, width=v["width"], fmt=fmt, src_path=dst):
                    with Image.open(src_path) as im:
                        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
                        height = max(1, round(im.height * width / im.width))
                        small = im.resize((width, height), Image.LANCZOS)
                        if fmt == "webp":
                            small.save(tmp, format="WEBP", quality=80, method=4)
                        else:
                            small.save(tmp, format="AVIF", quality=60)

                _atomic_write(vdst, render)
    return [n for n in _media_files(data) if (store / n).exists()]


def run_frontend_build(snapshot_path, out_dir, log_path):
    cmd = settings.FRONTEND_BUILD_CMD
    env = {**os.environ, "SNAPSHOT_PATH": str(snapshot_path), "BUILD_OUTPUT_DIR": str(out_dir)}
    for name in ("AGENT_HMAC_SECRET", "SECRET_KEY", "DATABASE_URL", "CMS_INTERNAL_SECRET"):
        env.pop(name, None)  # the frontend build never needs CMS secrets
    try:
        proc = subprocess.run(shlex.split(cmd), cwd=settings.BASE_DIR, env=env, capture_output=True, text=True,
                              timeout=settings.FRONTEND_BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"the frontend build took longer than {settings.FRONTEND_BUILD_TIMEOUT} s.") from None
    except FileNotFoundError:
        raise RuntimeError(f"the frontend build command was not found ({shlex.split(cmd)[0]}).") from None
    log_path.write_text(f"$ {cmd}\n--- stdout\n{proc.stdout}\n--- stderr\n{proc.stderr}\n", encoding="utf-8")
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-15:])
        raise RuntimeError(f"the frontend build exited with {proc.returncode}: {tail}")
    if not out_dir.is_dir() or not any(out_dir.iterdir()):
        raise RuntimeError(f"the frontend build produced no files in {out_dir.name}/.")


# ---- tarball ----------------------------------------------------------------------------------------------------
def _tarinfo(name, *, size=0, is_dir=False, mtime=0):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    info.mode = 0o755 if is_dir else 0o644
    info.size = 0 if is_dir else size
    info.mtime = mtime
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def pack_tarball(tar_path, *, site_dir, media_dir, media_all, media_new, snapshot_id, publish_id, mtime):
    """Deterministic tar.gz: sorted entries, fixed owner/mode/mtime, gzip header without name or time.

    Layout (contract §5 + publish-agent wire format): site/..., media/<new files>, manifest.json.
    """
    site_dir, media_dir = Path(site_dir), Path(media_dir)
    entries = []  # (arcname, path or bytes or None for dir)
    dirs = {"site", "media"}
    for path in sorted(site_dir.rglob("*")):
        rel = path.relative_to(site_dir).as_posix()
        if path.is_symlink():
            continue
        if path.is_dir():
            dirs.add(f"site/{rel}")
        elif path.is_file():
            entries.append((f"site/{rel}", path))
    for name in sorted(media_new):
        entries.append((f"media/{name}", media_dir / name))
    manifest = {"schema_version": 1, "snapshot_id": snapshot_id, "publish_id": publish_id,
                "media": sorted(media_all), "media_included": sorted(media_new)}
    entries.append(("manifest.json", (json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode()))
    entries += [(d, None) for d in dirs]
    entries.sort(key=lambda e: e[0])

    tar_path = Path(tar_path)
    tar_path.parent.mkdir(parents=True, exist_ok=True)

    def write(tmp):
        with open(tmp, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz, \
                tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for arcname, src in entries:
                if src is None:
                    tar.addfile(_tarinfo(arcname, is_dir=True, mtime=mtime))
                elif isinstance(src, bytes):
                    tar.addfile(_tarinfo(arcname, size=len(src), mtime=mtime), io.BytesIO(src))
                else:
                    with open(src, "rb") as fh:
                        tar.addfile(_tarinfo(arcname, size=os.path.getsize(src), mtime=mtime), fh)

    _atomic_write(tar_path, write)
    h = hashlib.sha256()
    with open(tar_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
