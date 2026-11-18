"""In-process test doubles: an SFTP server (paramiko) with fault injection, a fake CMS, a fake web server."""
from __future__ import annotations

import errno
import hashlib
import io
import json
import os
import posixpath
import re
import socket
import tarfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paramiko
from paramiko import SFTPAttributes, SFTPHandle, SFTPServer, SFTPServerInterface
from paramiko.sftp import SFTP_FAILURE, SFTP_OK

from publish_agent.cmsclient import build_signature, sign_request

HOME = "/home/u"


class Faults:
    def __init__(self):
        self.quota_bytes = None      # raise "Failure" on write once this many bytes were written
        self.written = 0
        self.drop_after_files = None  # close the connection when this many files were opened for writing
        self.files_opened = 0
        self.no_symlink = False
        self.no_posix_rename = False
        self.lock = threading.Lock()


class _Handle(SFTPHandle):
    def __init__(self, flags, faults):
        super().__init__(flags)
        self.faults = faults

    def write(self, offset, data):
        f = self.faults
        with f.lock:
            if f.quota_bytes is not None and f.written + len(data) > f.quota_bytes:
                return SFTPServer.convert_errno(errno.EDQUOT)
            f.written += len(data)
        return super().write(offset, data)

    def stat(self):
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)


class _SFTP(SFTPServerInterface):
    def __init__(self, server, *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.ctx = server.ctx

    def _real(self, path):
        return os.path.join(self.ctx.root, self.canonicalize(path).lstrip("/"))

    def canonicalize(self, path):
        if not path.startswith("/"):
            path = posixpath.join(HOME, path)
        return posixpath.normpath(path) or "/"

    def _err(self, exc):
        return SFTPServer.convert_errno(exc.errno)

    def list_folder(self, path):
        real = self._real(path)
        try:
            out = []
            for name in os.listdir(real):
                attr = SFTPAttributes.from_stat(os.lstat(os.path.join(real, name)))
                attr.filename = name
                out.append(attr)
            return out
        except OSError as e:
            return self._err(e)

    def stat(self, path):
        try:
            return SFTPAttributes.from_stat(os.stat(self._real(path)))
        except OSError as e:
            return self._err(e)

    def lstat(self, path):
        try:
            return SFTPAttributes.from_stat(os.lstat(self._real(path)))
        except OSError as e:
            return self._err(e)

    def open(self, path, flags, attr):
        real = self._real(path)
        f = self.ctx.faults
        writing = flags & (os.O_WRONLY | os.O_RDWR)
        if writing:
            with f.lock:
                f.files_opened += 1
                drop = f.drop_after_files is not None and f.files_opened > f.drop_after_files
                if drop:
                    f.drop_after_files = None
            if drop:
                self.ctx.drop_all()
                return SFTP_FAILURE
        try:
            fd = os.open(real, flags, 0o644)
        except OSError as e:
            return self._err(e)
        if (flags & os.O_CREAT) and attr is not None:
            attr._flags &= ~attr.FLAG_PERMISSIONS
        mode = "rb"
        if flags & os.O_WRONLY:
            mode = "ab" if flags & os.O_APPEND else "wb"
        elif flags & os.O_RDWR:
            mode = "a+b" if flags & os.O_APPEND else "r+b"
        fobj = os.fdopen(fd, mode)
        h = _Handle(flags, f)
        h.filename = real
        h.readfile = fobj
        h.writefile = fobj
        return h

    def remove(self, path):
        try:
            os.remove(self._real(path))
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def rename(self, oldpath, newpath):
        old, new = self._real(oldpath), self._real(newpath)
        if os.path.lexists(new):
            return SFTP_FAILURE
        try:
            os.rename(old, new)
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def posix_rename(self, oldpath, newpath):
        if self.ctx.faults.no_posix_rename:
            return paramiko.sftp.SFTP_OP_UNSUPPORTED
        try:
            os.replace(self._real(oldpath), self._real(newpath))
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def mkdir(self, path, attr):
        try:
            os.mkdir(self._real(path))
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def rmdir(self, path):
        try:
            os.rmdir(self._real(path))
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def chattr(self, path, attr):
        return SFTP_OK

    def symlink(self, target_path, path):
        if self.ctx.faults.no_symlink:
            return SFTP_FAILURE
        if target_path.startswith("/"):
            return SFTP_FAILURE  # tests only allow relative links (absolute ones break under chroot)
        try:
            os.symlink(target_path, self._real(path))
        except OSError as e:
            return self._err(e)
        return SFTP_OK

    def readlink(self, path):
        try:
            return os.readlink(self._real(path))
        except OSError as e:
            return self._err(e)


class _Server(paramiko.ServerInterface):
    def __init__(self, ctx):
        self.ctx = ctx

    def get_allowed_auths(self, username):
        return "publickey,password"

    def check_auth_publickey(self, username, key):
        if username == "u" and key.get_base64() == self.ctx.client_key.get_base64():
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        if username == "u" and password == self.ctx.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        return False  # SFTP-only account, like many shared hosts


class FakeSFTPServer:
    """Listens on 127.0.0.1:<free port>; maps the SFTP namespace onto self.root (home = /home/u)."""

    host_key = None

    def __init__(self, root: str, client_key, password: str = "local-test-pw"):
        if FakeSFTPServer.host_key is None:
            FakeSFTPServer.host_key = paramiko.RSAKey.generate(2048)
        self.root = root
        self.client_key = client_key
        self.password = password
        self.faults = Faults()
        os.makedirs(os.path.join(root, HOME.lstrip("/")), exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(20)
        self.port = self.sock.getsockname()[1]
        self.transports: list[paramiko.Transport] = []
        self._stop = False
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def home_path(self, *parts) -> str:
        return os.path.join(self.root, HOME.lstrip("/"), *parts)

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            t = paramiko.Transport(conn)
            t.add_server_key(self.host_key)
            t.set_subsystem_handler("sftp", SFTPServer, _SFTP)
            srv = _Server(self)
            try:
                t.start_server(server=srv)
            except (paramiko.SSHException, EOFError):
                continue
            self.transports.append(t)

    def drop_all(self):
        for t in list(self.transports):
            threading.Thread(target=t.close, daemon=True).start()

    def close(self):
        self._stop = True
        self.sock.close()
        for t in self.transports:
            t.close()

    def known_hosts_line(self) -> str:
        return f"[127.0.0.1]:{self.port} {self.host_key.get_name()} {self.host_key.get_base64()}\n"




# ------------------------------------------------------------------------------ builds
def make_build(snapshot_id: str, publish_id: str, pages: dict[str, str] | None = None,
               media: dict[str, bytes] | None = None, media_all: list[str] | None = None,
               marker: bool = True) -> bytes:
    pages = dict(pages or {})
    media = dict(media or {})
    meta = f'<meta name="crtdh-build" content="{snapshot_id}">' if marker else ""
    pages.setdefault("index.html", f"<html><head>{meta}</head><body>home {snapshot_id}</body></html>")
    pages.setdefault("about/index.html", f"<html><head>{meta}</head><body>about {snapshot_id}</body></html>")
    pages.setdefault("assets/app.js", "console.log(1)")
    manifest = {"schema_version": 1, "snapshot_id": snapshot_id, "publish_id": publish_id,
                "media": sorted(media_all if media_all is not None else media), "media_included": sorted(media)}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = int(time.time())
            tar.addfile(info, io.BytesIO(data))
        add("manifest.json", json.dumps(manifest).encode())
        for rel, text in pages.items():
            add(f"site/{rel}", text.encode())
        for name, data in media.items():
            add(f"media/{name}", data)
    return buf.getvalue()


def media_name(data: bytes, ext: str = "jpg") -> str:
    return f"{hashlib.sha256(data).hexdigest()[:16]}.{ext}"


# ------------------------------------------------------------------------------ fake CMS
class FakeCMS:
    def __init__(self, secret: str):
        self.secret = secret
        self.jobs: list[dict] = []      # queue; head is offered until it gets live/failed
        self.builds: dict[str, bytes] = {}
        self.statuses: list[dict] = []
        self.bad_auth = 0
        cms = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _auth(self, body: bytes) -> bool:
                ts = self.headers.get("X-Agent-Timestamp", "")
                sig = self.headers.get("X-Agent-Signature", "")
                if not ts.isdigit() or abs(time.time() - int(ts)) > 300:
                    return False
                exp = sign_request(cms.secret, self.command, self.path.split("?")[0], body, int(ts))
                ok = exp["X-Agent-Signature"] == sig
                if not ok:
                    cms.bad_auth += 1
                return ok

            def do_GET(self):
                if not self._auth(b""):
                    self.send_response(401); self.end_headers(); return
                if self.path == "/api/v1/agent/next/":
                    if not cms.jobs:
                        self.send_response(204); self.end_headers(); return
                    data = json.dumps(cms.jobs[0]).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                m = re.match(r"^/api/v1/agent/builds/(.+)\.tar\.gz$", self.path)
                if m and m.group(1) in cms.builds:
                    data = cms.builds[m.group(1)]
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_response(404); self.end_headers()

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if not self._auth(body):
                    self.send_response(401); self.end_headers(); return
                if self.path == "/api/v1/agent/status/":
                    st = json.loads(body)
                    cms.statuses.append(st)
                    if st["status"] in ("live", "failed") and cms.jobs and cms.jobs[0]["publish_id"] == st["publish_id"]:
                        cms.jobs.pop(0)
                    self.send_response(204); self.end_headers(); return
                self.send_response(404); self.end_headers()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def queue(self, snapshot_id: str, publish_id: str, data: bytes, tamper_sig=False, tamper_sha=False):
        sha = hashlib.sha256(data).hexdigest()
        sig = build_signature(self.secret, publish_id, snapshot_id, sha)
        if tamper_sig:
            sig = "0" * 64
        if tamper_sha:
            sha = hashlib.sha256(b"other").hexdigest()
            sig = build_signature(self.secret, publish_id, snapshot_id, sha)
        self.builds[publish_id] = data
        self.jobs.append({"publish_id": publish_id, "snapshot_id": snapshot_id,
                          "tarball_url": f"/api/v1/agent/builds/{publish_id}.tar.gz",
                          "sha256": sha, "signature": sig})

    def last(self, publish_id):
        return [s for s in self.statuses if s["publish_id"] == publish_id][-1]

    def close(self):
        self.httpd.shutdown()


# ------------------------------------------------------------------------------ fake web server
class FakeWeb:
    """Answers verify fetches by reading the server's files the way Apache would for each strategy."""

    def __init__(self, server: FakeSFTPServer, web_root="public_html"):
        self.server = server
        self.web_root = web_root
        self.calls = 0
        self.override = None  # callable(url) -> html, to simulate a broken site

    def __call__(self, url: str) -> str:
        self.calls += 1
        if self.override:
            return self.override(url)
        from urllib.parse import urlsplit
        path = urlsplit(url).path.lstrip("/")
        root = self.server.home_path(self.web_root)
        ht = os.path.join(root, ".htaccess")
        if os.path.exists(ht):
            m = re.search(r"# Live release: ([A-Za-z0-9._-]+)\.", open(ht).read())
            if m:
                root = os.path.join(root, "_crtdh", "releases", m.group(1))
        target = os.path.join(root, path)
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        with open(target, encoding="utf-8") as fh:
            return fh.read()
