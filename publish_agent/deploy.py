"""The publish flow: next -> download -> verify -> upload -> switch -> check live -> report -> clean up."""
from __future__ import annotations

import errno
import json
import os
import posixpath
import re
import shutil
import socket
import stat
import time
import urllib.parse
import urllib.request
import uuid
from typing import Callable

import paramiko

from . import strategies
from .bundle import Bundle, open_bundle, safe_id
from .cmsclient import BuildRejected, CMSClient, CMSError, Job, verify_job
from .config import STRATEGIES, Config
from .layout import (OUR_MEDIA, STAGING_MARKER, Layout, drop_meta, empty_state, load_state, read_meta, write_meta,
                     make_layout, save_state)
from .logutil import LOG
from .remote import Remote, RemoteError

CLEANUP_EVERY = 6 * 3600
MEDIA_INDEX_NAME = "index.html"  # written into the shared _media/ folder so it never lists its files
MEDIA_INDEX = b'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title></title>\n'


class PublishFailed(Exception):
    def __init__(self, step: str, message: str):
        super().__init__(message)
        self.step = step
        self.message = message


class Transient(Exception):
    """Connection-level problem; safe to retry and resume."""


def is_transient(exc: BaseException, remote: Remote | None) -> bool:
    if isinstance(exc, (EOFError, paramiko.SSHException, socket.timeout, ConnectionError, Transient)):
        return True
    if remote is not None:
        try:
            t = remote.sftp.get_channel().get_transport()
            if t is None or not t.is_active():
                return True
        except Exception:  # noqa: BLE001
            return True
    return False


def describe_write_error(exc: BaseException, what: str) -> str:
    code = getattr(exc, "errno", None)
    text = str(exc)
    if code in (errno.ENOSPC, getattr(errno, "EDQUOT", -1)) or re.search(r"(?i)quota|space|failure|size mismatch", text):
        return (f"the server refused to write {what} ({text or 'write failed'}). The disk quota is probably full: "
                "run `python -m publish_agent check` to see free space and remove old files.")
    if code == errno.EACCES or "permission" in text.lower():
        return f"permission denied writing {what} on the server"
    return f"could not write {what} on the server: {text or exc.__class__.__name__}"


def default_http_get(url: str, timeout: int = 20) -> str:
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):  # never file:, ftp: or custom schemes
        raise ValueError(f"only http(s) URLs can be checked, not {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "crtdh-publish-agent", "Cache-Control": "no-cache"})
    # nosec B310: scheme is restricted to http/https just above; the URL is the owner's verify_url
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        return resp.read(2_000_000).decode("utf-8", "replace")


def find_marker(html: str, name: str) -> str | None:
    for tag in re.findall(r"<meta\b[^>]*>", html, flags=re.I):
        if re.search(rf"""name\s*=\s*["']{re.escape(name)}["']""", tag, re.I):
            m = re.search(r"""content\s*=\s*["']([^"']*)["']""", tag, re.I)
            if m:
                return m.group(1)
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Publisher:
    def __init__(self, cfg: Config, cms: CMSClient | None = None,
                 connect: Callable[[], Remote] | None = None,
                 http_get: Callable[[str], str] = default_http_get,
                 sleep: Callable[[float], None] = time.sleep,
                 dry_run: bool = False, upload_attempts: int = 3):
        self.cfg = cfg
        self.cms = cms
        self._connect = connect or (lambda: Remote.connect(cfg))
        self.http_get = http_get
        self.sleep = sleep
        self.dry_run = dry_run
        self.upload_attempts = upload_attempts
        self._download_errors: tuple[str, int] = ("", 0)  # (publish_id, consecutive failed downloads)
        os.makedirs(cfg.work_dir, exist_ok=True)

    # ------------------------------------------------------------------ local state
    def local_state(self) -> dict:
        try:
            with open(self.cfg.local_state_file, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def save_local_state(self, **updates) -> None:
        data = self.local_state()
        data.update(updates)
        tmp = self.cfg.local_state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp, self.cfg.local_state_file)

    # ------------------------------------------------------------------ strategy/layout
    def resolve(self, remote: Remote) -> tuple[Layout, dict]:
        """Pick the strategy (config > what the server already uses > discovery) and load server state."""
        found = None
        for strat in STRATEGIES:
            try:
                lay = make_layout(self.cfg, remote, strat)
            except ValueError:
                continue
            st = remote.read_json(lay.state_file)
            if isinstance(st, dict) and st.get("strategy") == strat:
                found = (lay, st)
                break
        if self.cfg.strategy != "auto":
            if found and found[0].strategy != self.cfg.strategy:
                raise PublishFailed("switch", (
                    f"the server is set up for strategy '{found[0].strategy}' but the config says "
                    f"'{self.cfg.strategy}'. Set strategy = {found[0].strategy} (see README, 'Changing strategy')."))
            strategy = self.cfg.strategy
        elif found:
            strategy = found[0].strategy
        else:
            disc = self.local_state().get("discovery") or {}
            strategy = disc.get("recommended")
            if strategy not in STRATEGIES:
                from .discover import discover
                disc = discover(self.cfg, remote, http_get=self.http_get, probe_http=bool(self.cfg.verify_url))
                self.save_local_state(discovery=disc)
                strategy = disc.get("recommended")
            if strategy not in STRATEGIES:
                raise PublishFailed("switch", "could not choose a switch strategy; run `check` and set strategy in the config")
            LOG.info("strategy chosen from discovery: %s", strategy)
        layout = make_layout(self.cfg, remote, strategy)
        state = load_state(remote, layout)
        if not found:
            state = empty_state(strategy)
        if self.dry_run:
            if remote.lstat(layout.web_root) is None:
                LOG.warning("[dry-run] the web root is missing; a real run would restore it first")
        elif strategies.recover(remote, layout, state):
            save_state(remote, layout, state)
        self.reconcile(remote, layout, state)
        return layout, state

    def detect_live(self, remote: Remote, layout: Layout) -> str | None:
        """What the server is actually serving, regardless of what state.json says."""
        if layout.strategy == "symlink":
            if remote.islink(layout.web_root):
                try:
                    return posixpath.basename(remote.sftp.readlink(layout.web_root).rstrip("/"))
                except IOError:
                    return None
            return None
        if layout.strategy == "swap":
            # The live release is the one with metadata whose folder has moved out of releases/ (into the web root).
            if remote.lstat(layout.web_root) is None or not remote.isdir(layout.meta_dir):
                return None
            ids = [n[: -len(".json")] for n in remote.listdir(layout.meta_dir) if n.endswith(".json")]
            live = [r for r in ids if not remote.exists(layout.stored(r)) and not remote.exists(layout.staging(r))]
            return live[0] if len(live) == 1 else None
        if layout.strategy == "htaccess":
            raw = remote.read_bytes(posixpath.join(layout.web_root, ".htaccess")) or b""
            m = re.search(rb"# Live release: ([A-Za-z0-9._-]+)\.", raw)
            return m.group(1).decode() if m else None
        return None

    def reconcile(self, remote: Remote, layout: Layout, state: dict) -> None:
        live = self.detect_live(remote, layout)
        if live and live != state.get("current") and (live in state["history"] or
                                                      read_meta(remote, layout, live) is not None or
                                                      layout.strategy == "swap"):
            LOG.warning("server is serving %s but state said %s; correcting the state", live, state.get("current"))
            state["current"] = live
            if live not in state["history"]:
                state["history"].append(live)
                state["kinds"][live] = "legacy" if live.startswith("legacy-") else "release"
            if not self.dry_run:
                save_state(remote, layout, state)

    # ------------------------------------------------------------------ main entry points
    def run_once(self) -> str:
        assert self.cms is not None
        job = self.cms.next_job()
        if job is None:
            LOG.debug("nothing to publish")
            if not self.dry_run and time.time() - self.local_state().get("last_cleanup", 0) > CLEANUP_EVERY:
                self.idle_cleanup()
            return "idle"
        return self.deploy(job)

    def report(self, job: Job, status: str, step: str, message: str) -> None:
        if self.dry_run:
            LOG.info("[dry-run] would report %s/%s: %s", status, step, message)
            return
        LOG.info("status %s (%s): %s", status, step, message)
        self.cms.report(job.publish_id, status, step, message)

    def deploy(self, job: Job) -> str:
        LOG.info("publish %s: snapshot %s", job.publish_id, job.snapshot_id)
        self.save_local_state(last_job=job.publish_id, last_job_at=_now())
        step = "download"
        try:
            verify_job(self.cms.secret, job)
            sid = safe_id(job.snapshot_id)
            seen = self.local_state().get("published") or []
            # The last live publish may be offered again if our "live" report was lost: the server-side
            # check in _publish_on handles that case, so only older entries are refused here.
            if seen and seen[-1] == [job.publish_id, sid]:
                seen = seen[:-1]
            self._refuse_replay(job, sid, seen, None)
            self.report(job, "uploading", "download", "Downloading the build")
            try:
                bundle = self.fetch_bundle(job, sid)
            except CMSError as exc:
                return self._download_failed(job, exc)  # re-raises (retry with backoff) until the limit
            self._download_errors = ("", 0)
            step = "upload"
            self.report(job, "uploading", "upload", f"Uploading {len(bundle.site_files)} files")
            result = self.publish_bundle(job, bundle, sid)
        except BuildRejected as exc:
            return self._fail(job, "verify" if step == "download" else step, str(exc))
        except PublishFailed as exc:
            return self._fail(job, exc.step, exc.message)
        except CMSError as exc:
            LOG.warning("CMS problem, will retry: %s", exc)
            raise
        except Exception as exc:  # noqa: BLE001 - anything else must end this publish, or it blocks the queue
            LOG.debug("unexpected error detail", exc_info=True)
            return self._fail(job, step, f"unexpected error: {exc.__class__.__name__}: {exc}")
        if result == "live":
            shutil.rmtree(os.path.join(self.cfg.work_dir, sid), ignore_errors=True)
            for name in os.listdir(self.cfg.work_dir):
                if name.endswith(".tar.gz") and not name.startswith(sid):
                    os.remove(os.path.join(self.cfg.work_dir, name))
        return result

    def _download_failed(self, job: Job, exc: CMSError) -> str:
        pid, n = self._download_errors
        n = n + 1 if pid == job.publish_id else 1
        self._download_errors = (job.publish_id, n)
        limit = max(1, self.cfg.max_download_errors)
        if n < limit:
            LOG.warning("download %s/%s of publish %s failed", n, limit, job.publish_id)
            raise exc
        self._download_errors = ("", 0)
        return self._fail(job, "download", f"could not download the build after {n} attempts: {exc}")

    def _fail(self, job: Job, step: str, message: str) -> str:
        LOG.error("publish %s failed at %s: %s", job.publish_id, step, message)
        self.report(job, "failed", step, message)
        self.save_local_state(last_result="failed", last_error=f"{step}: {message}", last_result_at=_now())
        return "failed"

    def fetch_bundle(self, job: Job, sid: str) -> Bundle:
        tar_path = os.path.join(self.cfg.work_dir, f"{sid}.tar.gz")
        if os.path.exists(tar_path):
            import hashlib
            h = hashlib.sha256()
            with open(tar_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != job.sha256:
                os.remove(tar_path)
        if not os.path.exists(tar_path):
            self.cms.download(job, tar_path)
        return open_bundle(tar_path, os.path.join(self.cfg.work_dir, sid), job.snapshot_id, job.publish_id)

    # ------------------------------------------------------------------ remote part
    def publish_bundle(self, job: Job, bundle: Bundle, sid: str) -> str:
        last_exc: BaseException | None = None
        for attempt in range(1, self.upload_attempts + 1):
            remote = None
            try:
                remote = self._connect()
                return self._publish_on(remote, job, bundle, sid)
            except (PublishFailed, BuildRejected):
                raise
            except RemoteError as exc:
                if "host key" in str(exc) or "login failed" in str(exc) or attempt == self.upload_attempts:
                    raise PublishFailed("upload", str(exc)) from None
                last_exc = exc
            except Exception as exc:  # noqa: BLE001
                LOG.debug("upload error detail", exc_info=True)
                if not is_transient(exc, remote):
                    raise PublishFailed(getattr(exc, "_crtdh_step", "upload"),
                                        describe_write_error(exc, getattr(exc, "_crtdh_what", "files"))) from None
                last_exc = exc
            finally:
                if remote is not None:
                    try:
                        remote.close()
                    except Exception:  # noqa: BLE001
                        pass
            wait = 2 ** attempt
            LOG.warning("connection problem (%s); resuming in %ss (attempt %s/%s)",
                        last_exc or "unknown", wait, attempt, self.upload_attempts)
            self.sleep(wait)
        raise PublishFailed("upload", f"the connection to the server kept dropping: {last_exc}")

    def _publish_on(self, remote: Remote, job: Job, bundle: Bundle, sid: str) -> str:
        layout, state = self.resolve(remote)
        LOG.info("strategy %s, web root %s, release store %s", layout.strategy, layout.web_root, layout.base)

        if state.get("current") == sid:
            meta = read_meta(remote, layout, sid) or {}
            if meta.get("tarball_sha256") == job.sha256 and meta.get("publish_id") == job.publish_id:
                LOG.info("snapshot %s is already live; confirming", sid)
                ok, detail = self._check_live(job.snapshot_id)
                if not ok:
                    raise PublishFailed("check_live", f"release {sid} is switched in on the server, but the "
                                                      f"site does not show it ({detail})")
                self.report(job, "live", "check_live", f"Live (release {sid})")
                self.save_local_state(last_result="live", last_live=sid, last_result_at=_now())
                return "live"
        self._refuse_replay(job, sid, state.get("published") or [], state)

        if self.dry_run:
            return self._plan(remote, layout, state, bundle, sid)

        if state.get("current") is None and not state["history"]:
            self._first_takeover(remote, layout, state)

        self.cleanup(remote, layout, state, active=sid)
        self.upload_release(remote, layout, state, job, bundle, sid)

        self.report(job, "uploading", "switch", "Switching the site to the new release")
        previous = state.get("current")
        try:
            strategies.switch(remote, layout, state, sid, local_files=bundle.local_site_path)
        except Exception as exc:  # noqa: BLE001
            if is_transient(exc, remote):
                raise
            raise PublishFailed("switch", f"could not switch the site: {exc}") from None
        state["current"] = sid
        if sid not in state["history"]:
            state["history"].append(sid)
        state["kinds"][sid] = "release"
        state["published"] = ((state.get("published") or []) + [[job.publish_id, sid]])[-2000:]
        state.setdefault("live_at", {})[sid] = _now()
        save_state(remote, layout, state)

        ok, detail = self._check_live(job.snapshot_id)
        if not ok:
            msg = f"the site did not show the new build after switching ({detail})"
            if previous:
                strategies.switch(remote, layout, state, previous)
                state["current"] = previous
                save_state(remote, layout, state)
                msg += f"; rolled back to {previous}, live site unchanged"
            raise PublishFailed("check_live", msg)

        self.report(job, "live", "check_live", f"Live at {_now()} (release {sid})")
        self.save_local_state(published=((self.local_state().get("published") or []) + [[job.publish_id, sid]])[-2000:])
        self.save_local_state(last_result="live", last_live=sid, last_result_at=_now(), last_error="")
        try:
            self.cleanup(remote, layout, state, active=None)
            self.gc_media(remote, layout, state)
        except Exception as exc:  # noqa: BLE001 - the site is live; cleanup can wait for the next run
            LOG.warning("cleanup after publish failed (will retry next time): %s", exc)
        return "live"

    @staticmethod
    def _refuse_replay(job: Job, sid: str, published: list, state: dict | None) -> None:
        """A signed job that was already published must never be applied again (it would act as a rollback)."""
        for pid, old_sid in published:
            if pid == job.publish_id or old_sid == sid:
                raise PublishFailed("verify", (
                    f"publish {job.publish_id} / snapshot {sid} was already published before; refusing to apply it "
                    "again (an old signed build replayed would roll the site back). Use `rollback` on the PC "
                    "or publish a new snapshot from the CMS."))

    def _first_takeover(self, remote: Remote, layout: Layout, state: dict) -> None:
        from .discover import backup_live_site
        if remote.exists(layout.web_root) and not self.local_state().get("backup"):
            path = backup_live_site(self.cfg, remote, layout.web_root)
            self.save_local_state(backup=path)
        legacy = strategies.take_over(remote, layout, state)
        if legacy:
            state["current"] = legacy
            state["history"].append(legacy)
            state["kinds"][legacy] = "legacy"
        save_state(remote, layout, state)

    def upload_release(self, remote: Remote, layout: Layout, state: dict, job: Job, bundle: Bundle, sid: str) -> None:
        final = layout.stored(sid)
        meta = read_meta(remote, layout, sid)
        if meta and meta.get("tarball_sha256") == job.sha256 and remote.isdir(final):
            LOG.info("release %s already fully uploaded; skipping upload", sid)
            return
        if remote.exists(final):
            if state.get("current") == sid:
                raise PublishFailed("upload", f"release {sid} is live but differs from this build; refusing to touch it")
            remote.rmtree(final)
        staging = layout.staging(sid)
        smeta = remote.read_json(posixpath.join(staging, STAGING_MARKER))
        if remote.exists(staging) and not (isinstance(smeta, dict) and smeta.get("tarball_sha256") == job.sha256):
            remote.rmtree(staging)
        remote.makedirs(staging)
        remote.write_json(posixpath.join(staging, STAGING_MARKER), {"tarball_sha256": job.sha256, "started": _now()})

        existing = {rel: a.st_size for rel, a in remote.walk_files(staging)}
        made = {staging}
        uploaded = skipped = 0
        try:
            for rel, size in bundle.site_files:
                if existing.get(rel) == size:
                    skipped += 1
                    continue
                dest = posixpath.join(staging, rel)
                parent = posixpath.dirname(dest)
                if parent not in made:
                    remote.makedirs(parent)
                    made.add(parent)
                self._put(remote, bundle.local_site_path(rel), dest, rel)
                uploaded += 1
            LOG.info("site files: %s uploaded, %s already there", uploaded, skipped)

            remote.makedirs(layout.media_dir)
            have = {a.filename: a.st_size for a in remote.sftp.listdir_attr(layout.media_dir)}
            new_media = 0
            for name, size in bundle.media_files:
                if have.get(name) == size:
                    continue
                self._put(remote, bundle.local_media_path(name), posixpath.join(layout.media_dir, name), f"media/{name}")
                have[name] = size
                new_media += 1
            LOG.info("media: %s new, %s already on the server", new_media, len(bundle.media_files) - new_media)
            if have.get(MEDIA_INDEX_NAME) != len(MEDIA_INDEX):
                # /_media/ answers with an empty page instead of a file listing (the .htaccess no longer
                # turns listings off; frontend lane's request). Never a media name, so GC leaves it alone.
                remote.write_bytes(posixpath.join(layout.media_dir, MEDIA_INDEX_NAME), MEDIA_INDEX)
        except Exception as exc:
            if not is_transient(exc, remote):
                LOG.warning("removing the incomplete upload %s to free space", staging)
                try:
                    remote.rmtree(staging)
                except Exception:  # noqa: BLE001
                    pass
            raise
        if bundle.media_referenced is not None:
            missing = sorted(bundle.media_referenced - set(have))
            if missing:
                raise PublishFailed("upload", f"build uses {len(missing)} media file(s) that are neither on the server "
                                              f"nor in the build, e.g. {missing[0]}; the CMS must include them")
        strategies.prepare_release(remote, layout, staging)
        index_dirs = sorted({posixpath.dirname(r) for r, _ in bundle.site_files
                             if r.endswith("/index.html")} - {""})
        remote.sftp.remove(posixpath.join(staging, STAGING_MARKER))
        remote.sftp.rename(staging, final)
        # Written last: metadata present means the release folder is complete (a crash before this re-uploads).
        write_meta(remote, layout, sid, {
            # snapshot_id is the folder-safe id; build_id is the raw id the pages' crtdh-build meta carries.
            "publish_id": job.publish_id, "snapshot_id": sid, "build_id": job.snapshot_id, "tarball_sha256": job.sha256,
            "files": bundle.site_files, "index_dirs": index_dirs,
            "media": sorted(bundle.media_referenced) if bundle.media_referenced is not None else None,
            "uploaded_at": _now()})
        LOG.info("release %s uploaded to %s", sid, final)

    @staticmethod
    def _put(remote: Remote, local: str, dest: str, what: str) -> None:
        try:
            remote.put_file(local, dest)
        except Exception as exc:
            try:
                exc._crtdh_what = what  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            raise

    def _check_live(self, snapshot_id: str) -> tuple[bool, str]:
        """The page's <meta crtdh-build> carries the raw snapshot id (e.g. 2026-11-19T02:07:47Z-36dc5b), not the
        folder-safe form safe_id() makes of it."""
        if not self.cfg.verify_url:
            LOG.warning("verify_url not set; not checking the live site")
            return True, "not checked"
        detail = ""
        for attempt in range(1, max(1, self.cfg.verify_attempts) + 1):
            sep = "&" if "?" in self.cfg.verify_url else "?"
            url = f"{self.cfg.verify_url}{sep}crtdh-check={uuid.uuid4().hex[:8]}"
            try:
                html = self.http_get(url)
                found = find_marker(html, self.cfg.verify_marker)
                if found == snapshot_id:
                    LOG.info("live site shows build %s", snapshot_id)
                    return True, "ok"
                detail = f"found build marker {found!r}, expected {snapshot_id!r}"
            except Exception as exc:  # noqa: BLE001
                detail = f"could not load {self.cfg.verify_url}: {exc}"
            if attempt < self.cfg.verify_attempts:
                self.sleep(self.cfg.verify_delay)
        return False, detail

    def _plan(self, remote: Remote, layout: Layout, state: dict, bundle: Bundle, sid: str) -> str:
        have = {}
        if remote.isdir(layout.media_dir):
            have = {a.filename: a.st_size for a in remote.sftp.listdir_attr(layout.media_dir)}
        new_media = [(n, s) for n, s in bundle.media_files if have.get(n) != s]
        LOG.info("[dry-run] strategy %s; would upload %s site files (%.1f MB) to %s",
                 layout.strategy, len(bundle.site_files), bundle.site_bytes / 1e6, layout.stored(sid))
        LOG.info("[dry-run] would upload %s new media files (%.1f MB) to %s",
                 len(new_media), sum(s for _, s in new_media) / 1e6, layout.media_dir)
        LOG.info("[dry-run] would switch %s from %s to %s", layout.web_root, state.get("current") or "(existing site)", sid)
        return "dry-run"

    # ------------------------------------------------------------------ housekeeping
    def kept_ids(self, state: dict) -> set:
        cur = state.get("current")
        kinds = state.get("kinds", {})
        older = [r for r in reversed(state["history"]) if r != cur and kinds.get(r, "release") == "release"]
        kept = set(older[: self.cfg.keep_releases])
        kept |= {r for r in state["history"] if kinds.get(r) == "legacy"}
        if cur:
            kept.add(cur)
        return kept

    def cleanup(self, remote: Remote, layout: Layout, state: dict, active: str | None) -> None:
        """Delete stale staging folders, never-switched leftovers and releases beyond keep_releases."""
        kept = self.kept_ids(state)
        for name in remote.listdir(layout.releases):
            if name.endswith(".partial"):
                if name[: -len(".partial")] != active:
                    LOG.info("removing stale staging folder %s", name)
                    remote.rmtree(posixpath.join(layout.releases, name))
            elif name.startswith("legacy-") or name in kept or name == active:
                continue
            else:
                LOG.info("removing old release %s", name)
                remote.rmtree(posixpath.join(layout.releases, name))
                drop_meta(remote, layout, name)
        pruned = [r for r in state["history"] if r not in kept and r != active]
        if pruned:
            state["history"] = [r for r in state["history"] if r not in pruned]
            for r in pruned:
                state["kinds"].pop(r, None)
                state.get("live_at", {}).pop(r, None)
            save_state(remote, layout, state)
        self.save_local_state(last_cleanup=time.time())

    def gc_media(self, remote: Remote, layout: Layout, state: dict) -> int:
        refs: set = set()
        for rid in self.kept_ids(state):
            if state["kinds"].get(rid) == "legacy":
                continue
            meta = read_meta(remote, layout, rid)
            if meta is None or meta.get("media") is None:
                LOG.info("media list unknown for release %s; skipping media clean-up", rid)
                return 0
            refs |= set(meta["media"])
        removed = 0
        if not remote.isdir(layout.media_dir):
            return 0
        for attr in remote.sftp.listdir_attr(layout.media_dir):
            name = attr.filename
            if OUR_MEDIA.match(name) and name not in refs and stat.S_ISREG(attr.st_mode):
                remote.sftp.remove(posixpath.join(layout.media_dir, name))
                removed += 1
        if removed:
            LOG.info("removed %s media files no kept release uses", removed)
        return removed

    def idle_cleanup(self) -> None:
        remote = None
        try:
            remote = self._connect()
            layout, state = self.resolve(remote)
            if state.get("history"):
                self.cleanup(remote, layout, state, active=None)
                self.gc_media(remote, layout, state)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("idle clean-up skipped: %s", exc)
        finally:
            if remote:
                remote.close()

    # ------------------------------------------------------------------ operator commands
    def rollback(self, to: str | None = None) -> str:
        remote = self._connect()
        try:
            layout, state = self.resolve(remote)
            cur = state.get("current")
            hist = state["history"]
            if to:
                target = to
                if target not in hist:
                    raise PublishFailed("switch", f"{to} is not a kept release; kept: {', '.join(hist) or 'none'}")
            else:
                if cur not in hist or hist.index(cur) == 0:
                    raise PublishFailed("switch", "there is no earlier release to roll back to")
                target = hist[hist.index(cur) - 1]
            if target == cur:
                LOG.info("%s is already live", target)
                return target
            if self.dry_run:
                LOG.info("[dry-run] would roll back from %s to %s", cur, target)
                return target
            LOG.info("rolling back from %s to %s", cur, target)
            strategies.switch(remote, layout, state, target)
            state["current"] = target
            save_state(remote, layout, state)
            if state["kinds"].get(target) != "legacy":
                meta = read_meta(remote, layout, target) or {}
                ok, detail = self._check_live(meta.get("build_id") or target)
                if not ok:
                    LOG.warning("rolled back, but the live check did not confirm it: %s", detail)
            self.save_local_state(last_result="rolled back", last_live=target, last_result_at=_now())
            return target
        finally:
            remote.close()

    def status(self) -> dict:
        info = {"local": self.local_state()}
        remote = self._connect()
        try:
            layout, state = self.resolve(remote)
            info.update(strategy=layout.strategy, web_root=layout.web_root, release_store=layout.base,
                        current=state.get("current"), history=state.get("history"),
                        live_at=state.get("live_at", {}))
        finally:
            remote.close()
        return info
