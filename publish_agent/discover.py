"""Server discovery (WS0.7) and the one-off backup of the current live site.

Every probe creates its own uniquely named file or folder and removes it again.
"""
from __future__ import annotations

import io
import os
import posixpath
import stat
import tarfile
import time
import urllib.parse
import uuid
from typing import Callable

from .config import Config
from .logutil import LOG
from .remote import Remote

DISCOVER_SH = os.path.join(os.path.dirname(__file__), "discover.sh")


def _try(fn, *args):
    try:
        fn(*args)
        return True
    except Exception as exc:  # noqa: BLE001
        LOG.debug("probe %s failed: %s", getattr(fn, "__name__", fn), exc)
        return False


def discover(cfg: Config, remote: Remote, http_get: Callable[[str], str] | None = None,
             probe_http: bool = True) -> dict:
    r: dict = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "home": remote.home}
    web_root = remote.abspath(cfg.web_root)
    parent = posixpath.dirname(web_root)
    r["web_root"] = web_root
    st = remote.lstat(web_root)
    r["web_root_exists"] = st is not None
    r["web_root_is_link"] = bool(st and stat.S_ISLNK(st.st_mode))
    r["home_listing"] = [n for n in remote.listdir(remote.home) if not n.startswith(".")][:40]
    r["web_root_candidates"] = [n for n in r["home_listing"]
                                if n in ("public_html", "www", "htdocs", "html", "web", "httpdocs", "public")]
    if r["web_root_exists"]:
        r["web_root_entries"] = len(remote.listdir(web_root))

    tag = uuid.uuid4().hex[:8]
    # --- writable + rename + symlink, done next to the web root (where the switch happens)
    probe = posixpath.join(parent, f".crtdh-probe-{tag}")
    r["parent_writable"] = _try(remote.sftp.mkdir, probe)
    r["web_root_writable"] = False
    r["symlink_ok"] = r["rename_ok"] = r["posix_rename_ok"] = r["rename_into_web_root_ok"] = False
    if r["parent_writable"]:
        try:
            a = posixpath.join(probe, "a.txt")
            remote.write_bytes(a, b"crtdh")
            link = posixpath.join(probe, "link")
            if _try(remote.symlink, "a.txt", link):
                try:
                    r["symlink_ok"] = remote.sftp.readlink(link) == "a.txt" and remote.read_bytes(link) == b"crtdh"
                except IOError:
                    r["symlink_ok"] = False
            d1, d2 = posixpath.join(probe, "d1"), posixpath.join(probe, "d2")
            remote.sftp.mkdir(d1)
            r["rename_ok"] = _try(remote.sftp.rename, d1, d2)
            b = posixpath.join(probe, "b.txt")
            remote.write_bytes(b, b"new")
            r["posix_rename_ok"] = _try(remote.sftp.posix_rename, b, a) and remote.read_bytes(a) == b"new"
        finally:
            remote.rmtree(probe)
    if r["web_root_exists"]:
        wprobe = posixpath.join(web_root, f".crtdh-probe-{tag}")
        r["web_root_writable"] = _try(remote.sftp.mkdir, wprobe)
        if r["web_root_writable"] and r["parent_writable"]:
            moved = posixpath.join(parent, f".crtdh-probe-{tag}-moved")
            r["rename_into_web_root_ok"] = _try(remote.sftp.rename, wprobe, moved)
            remote.rmtree(moved)
        remote.rmtree(wprobe)

    # --- shell access (often disabled on SFTP-only accounts)
    res = remote.exec("probe")
    r["shell"] = bool(res and "crtdh-shell-ok" in res[1])
    if r["shell"]:
        try:
            with open(DISCOVER_SH, "rb") as fh:
                script = fh.read()
            out = remote.exec("discover", stdin=script, timeout=60, web_root=web_root)
            r["discover_sh"] = out[1] if out else ""
        except OSError:
            r["discover_sh"] = ""
        for line in r.get("discover_sh", "").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip() in ("php", "python3", "python", "perl", "free_kb", "quota", "passwd", "df"):
                    r[f"sh_{k.strip()}"] = v.strip()
    ssh_dir = posixpath.join(remote.home, ".ssh")
    r["ssh_dir_exists"] = remote.exists(ssh_dir)
    r["authorized_keys_exists"] = remote.exists(posixpath.join(ssh_dir, "authorized_keys"))

    # --- HTTP probes: does the web root map to the site URL; PHP; .htaccess; symlinks followed
    r["http"] = {}
    if probe_http and http_get and cfg.verify_url and r["web_root_writable"]:
        r["http"] = _http_probes(cfg, remote, web_root, http_get, tag)

    r["recommended"], r["why"] = recommend(r)
    return r


def _http_probes(cfg: Config, remote: Remote, web_root: str, http_get, tag: str) -> dict:
    out: dict = {}
    name = f"crtdh-probe-{tag}"
    d = posixpath.join(web_root, name)
    token = uuid.uuid4().hex
    base = urllib.parse.urljoin(cfg.verify_url, f"/{name}/")

    def fetch(f):
        try:
            return http_get(base + f).strip()
        except Exception as exc:  # noqa: BLE001
            return f"ERR {exc}"
    try:
        remote.sftp.mkdir(d)
        remote.write_bytes(posixpath.join(d, "t.txt"), token.encode())
        remote.write_bytes(posixpath.join(d, "p.php"), b'<?php echo "php-" . (40 + 2); ?>')
        remote.write_bytes(posixpath.join(d, ".htaccess"),
                           b"RewriteEngine On\nRewriteRule ^r\\.txt$ t.txt [L]\n")
        _try(remote.symlink, "t.txt", posixpath.join(d, "l.txt"))
        out["web_root_matches_url"] = fetch("t.txt") == token
        if out["web_root_matches_url"]:
            out["php"] = fetch("p.php") == "php-42"
            out["htaccess"] = fetch("r.txt") == token
            out["symlinks_followed"] = fetch("l.txt") == token
    finally:
        remote.rmtree(d)
    return out


def recommend(r: dict) -> tuple[str, str]:
    http = r.get("http") or {}
    if not r.get("web_root_exists"):
        return "", "web root not found: set web_root in the config"
    if r.get("parent_writable") and r.get("symlink_ok") and r.get("rename_ok") and r.get("posix_rename_ok") \
            and http.get("symlinks_followed") is not False:
        return "symlink", "symlinks and atomic rename work next to the web root (zero-downtime switch)"
    if http.get("htaccess"):
        return "htaccess", ".htaccess rewrites are honoured; one-file switch (zero downtime)"
    if r.get("parent_writable") and r.get("rename_ok") and r.get("rename_into_web_root_ok"):
        return "swap", "folder rename works; switch has a sub-second gap while folders are swapped"
    if r.get("web_root_writable"):
        return "copy", "only the web root is writable; files are replaced one by one (last resort)"
    return "", "web root is not writable by this account"


def format_report(r: dict) -> str:
    def yn(v):
        return {True: "yes", False: "no", None: "unknown"}.get(v, str(v))
    http = r.get("http") or {}
    lines = [
        f"Home folder            : {r.get('home')}",
        f"Web root               : {r.get('web_root')} (exists: {yn(r.get('web_root_exists'))}, "
        f"is link: {yn(r.get('web_root_is_link'))}, entries: {r.get('web_root_entries', '-')})",
        f"Other web-root folders : {', '.join(r.get('web_root_candidates') or []) or '-'}",
        f"Web root writable      : {yn(r.get('web_root_writable'))}",
        f"Its parent writable    : {yn(r.get('parent_writable'))}",
        f"Symlinks allowed       : {yn(r.get('symlink_ok'))}",
        f"Folder rename works    : {yn(r.get('rename_ok'))} (atomic replace: {yn(r.get('posix_rename_ok'))})",
        f"Shell (ssh commands)   : {yn(r.get('shell'))}",
        f"PHP / Python on server : {r.get('sh_php', 'unknown')} / {r.get('sh_python3', 'unknown')}",
        f"Free space (KB)        : {r.get('sh_free_kb', 'unknown (no shell; check the hosting panel)')}",
        f"Quota                  : {r.get('sh_quota', 'unknown')}",
        f"passwd available       : {r.get('sh_passwd', 'unknown')}",
        f"~/.ssh exists          : {yn(r.get('ssh_dir_exists'))} (authorized_keys: {yn(r.get('authorized_keys_exists'))})",
    ]
    if http:
        lines += [
            f"URL serves web root    : {yn(http.get('web_root_matches_url'))}",
            f"PHP runs over HTTP     : {yn(http.get('php'))}",
            f".htaccess honoured     : {yn(http.get('htaccess'))}",
            f"Symlinks followed      : {yn(http.get('symlinks_followed'))}",
        ]
    else:
        lines.append("HTTP checks            : skipped (set verify_url in the config to enable)")
    lines.append(f"RECOMMENDED STRATEGY   : {r.get('recommended') or 'none'} — {r.get('why')}")
    return "\n".join(lines)


def backup_live_site(cfg: Config, remote: Remote, web_root: str) -> str:
    """Download everything under the web root into a local .tar.gz before the agent first changes it."""
    os.makedirs(cfg.backup_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(cfg.backup_dir, f"live-site-before-agent-{stamp}.tar.gz")
    tmp = path + ".partial"
    count = 0
    skipped: list[str] = []
    LOG.info("backing up the current live site %s to %s (first publish only)", web_root, path)
    with tarfile.open(tmp, "w:gz") as tar:
        def walk(rdir: str, prefix: str):
            nonlocal count
            for attr in remote.sftp.listdir_attr(rdir):
                rel = f"{prefix}{attr.filename}"
                full = posixpath.join(rdir, attr.filename)
                if stat.S_ISDIR(attr.st_mode):
                    if attr.filename == "_crtdh" and not prefix:
                        continue
                    walk(full, rel + "/")
                elif stat.S_ISREG(attr.st_mode):
                    info = tarfile.TarInfo("site/" + rel)
                    info.size = attr.st_size
                    info.mtime = attr.st_mtime or 0
                    with remote.sftp.open(full, "rb") as fh:
                        fh.prefetch(attr.st_size)
                        tar.addfile(info, fh)
                    count += 1
                else:
                    target = ""
                    try:
                        target = remote.sftp.readlink(full)
                    except IOError:
                        pass
                    skipped.append(f"{rel} -> {target}")
        root = web_root
        if remote.islink(web_root):
            root = remote.sftp.normalize(web_root)
        walk(root, "")
        note = (f"Backup of {web_root} taken {stamp} by the CRTDH publish agent. {count} files.\n"
                "Links (not followed):\n" + "\n".join(skipped) + "\n").encode()
        info = tarfile.TarInfo("BACKUP-README.txt")
        info.size = len(note)
        tar.addfile(info, io.BytesIO(note))
    os.replace(tmp, path)
    LOG.info("backup done: %s files", count)
    return path
