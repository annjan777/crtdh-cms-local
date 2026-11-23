"""The four ways to make an uploaded release live. Each switch is undoable by switching back."""
from __future__ import annotations

import os
import posixpath
import re
import stat
import tempfile
import time
from typing import Callable

from .bundle import MEDIA_PREFIX
from .layout import Layout, read_meta, save_state
from .logutil import LOG
from .remote import Remote, RemoteError

HTACCESS_BEGIN = "# BEGIN crtdh-publish-agent"
HTACCESS_END = "# END crtdh-publish-agent"
LEGACY_HTACCESS = "legacy.htaccess"
_APACHE_SAFE = re.compile(r"^[A-Za-z0-9._/-]+$")


def _ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


# ---------------------------------------------------------------------------- first takeover
def take_over(remote: Remote, layout: Layout, state: dict) -> str | None:
    """Keep the existing (pre-agent) site reachable for rollback. Returns its legacy id."""
    if layout.strategy == "copy":
        return None
    if layout.strategy == "htaccess":
        legacy = remote.read_bytes(posixpath.join(layout.web_root, ".htaccess"))
        remote.makedirs(layout.base)
        remote.write_bytes(posixpath.join(layout.base, LEGACY_HTACCESS), legacy or b"")
        return "legacy-" + _ts()
    st = remote.lstat(layout.web_root)
    if st is None:
        return None
    rid = "legacy-" + _ts()
    remote.makedirs(layout.releases)
    if layout.strategy == "symlink":
        if stat.S_ISLNK(st.st_mode):
            # The web root is already a link (e.g. to a folder managed elsewhere): leave that folder where it
            # is and remember where the link pointed, so rollback can point back at it.
            target = remote.sftp.normalize(layout.web_root)
            state.setdefault("legacy_targets", {})[rid] = target
            LOG.info("first publish: the web root is a link to %s; recorded it as %s", target, rid)
            return rid
        LOG.info("first publish: moving the existing site %s to %s", layout.web_root, layout.stored(rid))
        remote.sftp.rename(layout.web_root, layout.stored(rid))
        # Point the web root at the old site straight away; recover() repairs a crash between these two calls.
        remote.symlink(posixpath.relpath(layout.stored(rid), posixpath.dirname(layout.web_root)), layout.web_root)
    # swap: the old site stays in the web root (it is now "current"); the first switch moves it to releases/<id>.
    return rid


# ---------------------------------------------------------------------------- crash recovery
def recover(remote: Remote, layout: Layout, state: dict) -> bool:
    """Repair a web root left missing by a dropped connection or a crash part-way through a switch.

    Returns True if something was repaired (the caller saves the state)."""
    if layout.strategy == "swap":
        return _recover_swap(remote, layout, state)
    if layout.strategy == "symlink" and remote.lstat(layout.web_root) is None:
        cur = state.get("current")
        dest = None
        if cur:
            dest = (state.get("legacy_targets") or {}).get(cur) or layout.stored(cur)
        if not dest or not remote.exists(dest):
            legacy = sorted(n for n in remote.listdir(layout.releases) if n.startswith("legacy-")
                            and not n.endswith(".partial"))
            dest = layout.stored(legacy[-1]) if legacy else None
        if not dest or not remote.exists(dest):
            raise RemoteError(f"{layout.web_root} is missing and no release was found to restore it; "
                              "see the README runbook")
        LOG.error("web root %s was missing (interrupted switch); pointing it back at %s", layout.web_root, dest)
        remote.symlink(posixpath.relpath(dest, posixpath.dirname(layout.web_root)), layout.web_root)
        return True
    return False


def _recover_swap(remote: Remote, layout: Layout, state: dict) -> bool:
    sw = state.get("switching") or {}
    if remote.exists(layout.web_root):
        if sw:
            state.pop("switching", None)  # either never started or finished; reconcile() reads the marker
            return True
        return False
    frm = sw.get("from") or state.get("current")
    to = sw.get("to")
    out = layout.stored(frm) if frm else None
    if not out or not remote.exists(out):
        raise RemoteError(f"{layout.web_root} is missing and the previous site ({frm}) was not found; "
                          "see the README runbook")
    out_media = posixpath.join(out, MEDIA_PREFIX)
    if to and not remote.exists(out_media):
        moved = posixpath.join(layout.stored(to), MEDIA_PREFIX)
        if remote.exists(moved):
            remote.sftp.rename(moved, out_media)
    LOG.error("web root %s was missing (interrupted swap); putting %s back", layout.web_root, frm)
    remote.sftp.rename(out, layout.web_root)
    state.pop("switching", None)
    state["current"] = frm
    return True


# ---------------------------------------------------------------------------- per-release prep
def prepare_release(remote: Remote, layout: Layout, staging: str) -> None:
    if layout.strategy == "symlink":
        link = posixpath.join(staging, MEDIA_PREFIX)
        if not remote.exists(link):
            remote.symlink(posixpath.relpath(layout.media_dir, staging), link)


# ---------------------------------------------------------------------------- switch
def switch(remote: Remote, layout: Layout, state: dict, target: str,
           local_files: Callable[[str], str] | None = None) -> None:
    kind = state["kinds"].get(target, "release")
    fn = {"symlink": _switch_symlink, "htaccess": _switch_htaccess,
          "swap": _switch_swap, "copy": _switch_copy}[layout.strategy]
    fn(remote, layout, state, target, kind, local_files)


def _switch_symlink(remote, layout, state, target, kind, _local):
    dest = (state.get("legacy_targets") or {}).get(target) or layout.stored(target)
    if not remote.exists(dest):
        raise RemoteError(f"release {target} is missing on the server")
    rel = posixpath.relpath(dest, posixpath.dirname(layout.web_root))
    tmp = layout.web_root + ".crtdh-new"
    remote.rmtree(tmp)
    remote.symlink(rel, tmp)
    st = remote.lstat(layout.web_root)
    if st is not None and not stat.S_ISLNK(st.st_mode):
        raise RemoteError(f"{layout.web_root} is a real folder, not the agent's link; refusing to replace it")
    remote.replace(tmp, layout.web_root)  # atomic rename of the link


# One-line redirects from the build's own .htaccess (the old site's /about.html etc., frontend/scripts/postbuild.mjs).
# In the htaccess strategy every request is rewritten into releases/<id>/ first, so the build's RedirectMatch lines
# would only ever see the rewritten path; they are copied up here as RewriteRules that run before that. Only this
# exact, plain shape is accepted, so nothing else in a build can reach the top-level .htaccess.
_REDIRECT_LINE = re.compile(r"^\s*RedirectMatch (301|410) \^/((?:[A-Za-z0-9_-]|\\\.)+)\$(?: (/[A-Za-z0-9_/-]*))?\s*$")


def build_redirects(htaccess_text: str) -> list:
    """[(status, escaped path without the leading slash, target or None)] from a build's .htaccess."""
    out = []
    for line in htaccess_text.splitlines():
        m = _REDIRECT_LINE.match(line)
        if not m:
            continue
        status, path, target = m.group(1), m.group(2), m.group(3)
        if (status == "301") != bool(target):
            continue
        out.append((status, path, target))
    return out


def htaccess_rules(layout: Layout, target: str, index_dirs: list, redirects: list | None = None) -> str:
    rel = posixpath.relpath(layout.base, layout.web_root)
    rel_release = f"{rel}/releases/{target}"
    if not (_APACHE_SAFE.match(rel_release) and _APACHE_SAFE.match(rel)):
        raise RemoteError("folder names contain characters unsafe for .htaccess")
    esc = re.escape
    lines = [
        HTACCESS_BEGIN,
        f"# Live release: {target}. Written by the CRTDH publish agent; edits inside this block are overwritten,",
        "# rules outside it are kept.",
        # No "Options": on a host with AllowOverride FileInfo only, any Options line makes every request a 500.
        # Listings are not needed off: every folder of a build has an index.html, and so does _media/.
        "RewriteEngine On",
        "RewriteBase /",
    ]
    if redirects:
        lines.append("# The old site's addresses (from this release's own .htaccess)")
        for status, path, to in redirects:
            lines.append(f"RewriteRule ^{path}$ {to} [R=301,L]" if status == "301" else f"RewriteRule ^{path}$ - [G,L]")
    lines += [
        "# Block direct requests to the release store",
        "RewriteCond %{ENV:REDIRECT_STATUS} ^$",
        f"RewriteRule ^{esc(rel)}(/|$) - [F,L]",
        f"RewriteRule ^{MEDIA_PREFIX}/(.+)$ {rel}/{MEDIA_PREFIX}/$1 [L]",
        f"RewriteRule ^$ {rel_release}/index.html [L]",
    ]
    dirs = sorted(d for d in index_dirs if d and _APACHE_SAFE.match(d))
    if dirs:
        alt = "|".join(esc(d) for d in dirs)
        lines.append(f"RewriteRule ^({alt})/?$ {rel_release}/$1/index.html [L]")
    lines += [
        f"RewriteCond %{{REQUEST_URI}} !^/{esc(rel)}/",
        f"RewriteRule ^(.*)$ {rel_release}/$1 [L]",
        HTACCESS_END,
        "",
    ]
    return "\n".join(lines)


_BLOCK = re.compile(re.escape(HTACCESS_BEGIN) + r".*?" + re.escape(HTACCESS_END) + r"\n?", re.S)


def strip_block(text: str) -> str:
    return _BLOCK.sub("", text)


def _switch_htaccess(remote, layout, state, target, kind, _local):
    """Replace only the agent's BEGIN/END block; every other line of .htaccess is kept as it was."""
    path = posixpath.join(layout.web_root, ".htaccess")
    raw = remote.read_bytes(path)
    rest = strip_block((raw or b"").decode("latin-1"))
    if kind == "legacy":
        if rest.strip():
            remote.write_bytes(path, rest.encode("latin-1"))
        elif raw is not None:
            remote.sftp.remove(path)
        return
    meta = read_meta(remote, layout, target) or {}
    if not meta:
        raise RemoteError(f"release {target} is missing or incomplete on the server")
    own = remote.read_bytes(posixpath.join(layout.stored(target), ".htaccess")) or b""
    block = htaccess_rules(layout, target, meta.get("index_dirs", []), build_redirects(own.decode("latin-1")))
    remote.write_bytes(path, (block + rest).encode("latin-1"))


def _switch_swap(remote, layout, state, target, kind, _local):
    if _recover_swap(remote, layout, state):
        save_state(remote, layout, state)
    current = state.get("current")
    src = layout.stored(target)
    if not remote.exists(src):
        raise RemoteError(f"release {target} is missing on the server")
    if not current and not remote.exists(layout.web_root):
        remote.sftp.rename(src, layout.web_root)
        return
    if not current:
        raise RemoteError("swap strategy: cannot tell which release is live; refusing to touch the web root")
    out = layout.stored(current)
    if remote.exists(out):
        raise RemoteError(f"{out} already exists; refusing to overwrite it")
    incoming_media = posixpath.join(src, MEDIA_PREFIX)
    if remote.exists(incoming_media):
        remote.sftp.rename(incoming_media, posixpath.join(src, f"{MEDIA_PREFIX}.stale-{_ts()}"))
    # Record the intent first: if the connection or the PC dies inside the window below, recover() on the
    # next connection knows which folder to put back.
    state["switching"] = {"from": current, "to": target}
    save_state(remote, layout, state)
    # Non-atomic window: the web root is missing between rename 1 and rename 3.
    remote.sftp.rename(layout.web_root, out)
    try:
        if remote.exists(posixpath.join(out, MEDIA_PREFIX)):
            remote.sftp.rename(posixpath.join(out, MEDIA_PREFIX), incoming_media)
        remote.sftp.rename(src, layout.web_root)
    except Exception:
        LOG.error("swap failed half way; putting the previous site back")
        try:
            _recover_swap(remote, layout, state)
            save_state(remote, layout, state)
        except Exception as exc:  # noqa: BLE001 - connection gone: the next run recovers from state["switching"]
            LOG.error("could not put the previous site back now (%s); the next run will", exc)
        raise
    state.pop("switching", None)


def _switch_copy(remote, layout, state, target, kind, local_files):
    """Last resort: overwrite files in the web root one by one (each file swap is atomic, the set is not)."""
    src = layout.stored(target)
    meta = read_meta(remote, layout, target) or {}
    files = [f for f, _ in meta.get("files", [])]
    if not files:
        raise RemoteError(f"release {target} is missing or incomplete on the server")
    tmpdir = None
    if local_files is None:
        tmpdir = tempfile.mkdtemp(prefix="crtdh-copy-")

        def local_files(rel, _tmp=tmpdir):  # noqa: F811 - download from the stored release
            dest = os.path.join(_tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            remote.sftp.get(posixpath.join(src, rel), dest)
            return dest
    made = set()
    try:
        for rel in files:
            dest = posixpath.join(layout.web_root, rel)
            parent = posixpath.dirname(dest)
            if parent not in made:
                remote.makedirs(parent)
                made.add(parent)
            remote.put_file(local_files(rel), dest)
    finally:
        if tmpdir:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    previous = state.get("current")
    if previous and previous != target:
        old = read_meta(remote, layout, previous) or {}
        keep = set(files)
        for rel, _ in old.get("files", []):
            if rel not in keep and not rel.startswith(MEDIA_PREFIX + "/"):
                try:
                    remote.sftp.remove(posixpath.join(layout.web_root, rel))
                except IOError:
                    pass
