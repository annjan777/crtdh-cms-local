"""Regression tests for the review findings (FIX FIRST list) and contract addendum A13."""
import io
import json
import os
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paramiko
import pytest

from publish_agent.cmsclient import Job, build_signature
from publish_agent.config import ConfigError, validate

from .conftest import SECRET
from .fakes import F1, F2, S1, S2, S3, make_build, media_name


def live(pub, path=""):
    return pub.web(f"https://crtdh.example/{path}")


def publish(cms, pub, sid, pid, **kw):
    cms.queue(sid, pid, make_build(sid, pid, **kw))
    return pub.run_once()


def raw_tar(entries):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _hook_rename_of_web_root(monkeypatch, action):
    """Run `action(sftp)` right after the swap renames the web root away (rename 1 of 3), once."""
    real = paramiko.SFTPClient.rename
    fired = {"n": 0}

    def rename(self, old, new):
        real(self, old, new)
        if old.endswith("/public_html") and "/releases/" in new and fired["n"] == 0:
            fired["n"] += 1
            action(self)
    monkeypatch.setattr(paramiko.SFTPClient, "rename", rename)
    return fired


# ------------------------------------------------------------------ HIGH 1: swap window
def test_swap_connection_drop_inside_window_recovers_same_run(make_pub, cms, server, monkeypatch):
    pub = make_pub(strategy="swap")
    assert publish(cms, pub, S1, "p1") == "live"

    def drop(sftp):
        sftp.get_channel().get_transport().close()
        raise EOFError("connection lost")
    fired = _hook_rename_of_web_root(monkeypatch, drop)
    assert publish(cms, pub, S2, "p2") == "live"
    assert fired["n"] == 1
    assert f"home {S2}" in live(pub)
    assert cms.last("p2")["status"] == "live"
    state = json.load(open(server.home_path("crtdh-releases", "state.json")))
    assert state["current"] == F2 and "switching" not in state


def test_swap_pc_crash_inside_window_next_run_restores_site(make_pub, cms, server, monkeypatch):
    pub = make_pub(strategy="swap")
    assert publish(cms, pub, S1, "p1") == "live"

    def crash(_sftp):
        raise SystemExit("power cut")
    _hook_rename_of_web_root(monkeypatch, crash)
    cms.queue(S2, "p2", make_build(S2, "p2"))
    with pytest.raises(SystemExit):
        pub.run_once()
    assert not os.path.exists(server.home_path("public_html"))  # site is down right now
    monkeypatch.undo()
    st = pub.status()  # any command that connects repairs it first
    assert st["current"] == F1
    assert f"home {S1}" in live(pub)
    assert pub.run_once() == "live"  # and the pending publish then completes
    assert f"home {S2}" in live(pub)


def test_symlink_crash_during_takeover_restores_link(make_pub, cms, server, monkeypatch):
    pub = make_pub(strategy="symlink")
    real_symlink = paramiko.SFTPClient.symlink
    state = {"n": 0}

    def symlink(self, src, dst):
        if dst.endswith("/public_html") and state["n"] == 0:
            state["n"] += 1
            raise SystemExit("power cut")
        return real_symlink(self, src, dst)
    monkeypatch.setattr(paramiko.SFTPClient, "symlink", symlink)
    cms.queue(S1, "p1", make_build(S1, "p1"))
    with pytest.raises(SystemExit):
        pub.run_once()
    assert not os.path.lexists(server.home_path("public_html"))
    monkeypatch.undo()
    assert pub.run_once() == "live"
    assert f"home {S1}" in live(pub)
    assert pub.rollback().startswith("legacy-")
    assert "old site" in live(pub)


# ------------------------------------------------------------------ HIGH 2: path escapes
@pytest.mark.parametrize("bad", [
    "site/D:evil.html", "site/C:/x.html", "site/a\\b.html", "site/CON", "site/nul.txt", "site/lpt1.js",
    "site/trailing.", "site/sp ace.html", "site/x:stream", "site/_media/aaaaaaaaaaaaaaaa.jpg",
])
def test_unsafe_names_rejected(make_pub, cms, server, bad):
    pub = make_pub()
    data = raw_tar([("manifest.json", b"{}"), ("site/index.html", b"x"), (bad, b"evil")])
    cms.queue(S1, "p1", data)
    assert pub.run_once() == "failed"
    msg = cms.last("p1")["message"]
    assert "unsafe path" in msg or "reserved" in msg
    assert "old site" in live(pub)


def test_symlink_in_work_dir_cannot_escape(tmp_path):
    from publish_agent.bundle import BuildRejected, open_bundle
    tar_path = tmp_path / "b.tar.gz"
    tar_path.write_bytes(raw_tar([("manifest.json", b"{}"), ("site/index.html", b"x"), ("site/sub/a.html", b"y")]))
    dest = tmp_path / "out"
    # a pre-existing link inside the unpack folder would be removed first; simulate an attacker-placed one
    # by unpacking into a folder whose child is a link pointing outside, after the rmtree step.
    import publish_agent.bundle as b
    real = b.os.makedirs

    def makedirs(path, *a, **k):
        if str(path).endswith(os.path.join("site", "sub")) and not os.path.lexists(path):
            os.symlink(str(tmp_path), path)
            return
        return real(path, *a, **k)
    b.os.makedirs = makedirs
    try:
        with pytest.raises(BuildRejected, match="unsafe path"):
            open_bundle(str(tar_path), str(dest), S1, "p1")
    finally:
        b.os.makedirs = real


# ------------------------------------------------------------------ MED: every failure is reported
def test_file_then_dir_with_same_name_reported_failed(make_pub, cms, server):
    pub = make_pub()
    data = raw_tar([("manifest.json", b"{}"), ("site/index.html", b"x"), ("site/x", b"file"), ("site/x/y", b"z")])
    cms.queue(S1, "p1", data)
    assert pub.run_once() == "failed"
    assert "cannot be unpacked" in cms.last("p1")["message"]
    assert not cms.jobs  # the queue is not blocked


def test_non_hex_signature_reported_failed(make_pub, cms, server):
    pub = make_pub()
    cms.queue(S1, "p1", make_build(S1, "p1"))
    cms.jobs[0]["signature"] = "\u00e9" * 64
    assert pub.run_once() == "failed"
    st = cms.last("p1")
    assert st["step"] == "verify" and "malformed" in st["message"]


def test_unexpected_exception_reported_failed(make_pub, cms, server, monkeypatch):
    pub = make_pub()

    def boom(*a, **k):
        raise RuntimeError("local disk exploded")
    monkeypatch.setattr(pub, "publish_bundle", boom)
    cms.queue(S1, "p1", make_build(S1, "p1"))
    assert pub.run_once() == "failed"
    st = cms.last("p1")
    assert st["status"] == "failed" and "RuntimeError" in st["message"]
    assert not cms.jobs


# ------------------------------------------------------------------ MED: https + replay
@pytest.mark.parametrize("url,ok", [
    ("https://cms.example", True), ("http://127.0.0.1:8500", True), ("http://localhost:8500", True),
    ("http://cms.example", False), ("ftp://cms.example", False), ("https://", False),
])
def test_cms_url_must_be_https(make_cfg, url, ok):
    cfg = make_cfg()
    cfg.cms_url = url
    if ok:
        validate(cfg)
    else:
        with pytest.raises(ConfigError, match="https"):
            validate(cfg)


@pytest.mark.parametrize("wipe_local", [False, True])
def test_replayed_old_job_is_refused(make_pub, cms, server, wipe_local):
    pub = make_pub()
    old = make_build(S1, "p1")
    cms.queue(S1, "p1", old)
    assert pub.run_once() == "live"
    assert publish(cms, pub, S2, "p2") == "live"
    if wipe_local:  # a new PC: the server-side record still refuses it
        os.remove(pub.cfg.local_state_file)
    cms.queue(S1, "p1", old)
    assert pub.run_once() == "failed"
    assert "already published" in cms.last("p1")["message"]
    assert f"home {S2}" in live(pub)
    # same old snapshot under a new publish id is refused too
    cms.queue(S1, "p9", make_build(S1, "p9"))
    assert pub.run_once() == "failed"
    assert f"home {S2}" in live(pub)


# ------------------------------------------------------------------ MED: symlinked web root takeover
def test_symlinked_web_root_is_recorded_not_moved(make_pub, cms, server):
    import shutil
    wr = server.home_path("public_html")
    os.makedirs(server.home_path("sites"))
    shutil.move(wr, server.home_path("sites", "crtdh"))
    os.symlink("sites/crtdh", wr)
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    assert os.path.isdir(server.home_path("sites", "crtdh"))  # untouched
    state = json.load(open(server.home_path("crtdh-releases", "state.json")))
    legacy = [r for r in state["history"] if r.startswith("legacy-")][0]
    assert state["legacy_targets"][legacy] == "/home/u/sites/crtdh"
    assert pub.rollback() == legacy
    assert os.readlink(wr) == "sites/crtdh"
    assert "old site" in live(pub)


# ------------------------------------------------------------------ MED: htaccess keeps other rules
def test_htaccess_keeps_rules_outside_block(make_pub, cms, server):
    ht = server.home_path("public_html", ".htaccess")
    with open(ht, "w") as fh:
        fh.write("# owner rules\nErrorDocument 404 /404.html\nHeader set X-Test yes\n")
    pub = make_pub(strategy="htaccess")
    assert publish(cms, pub, S1, "p1") == "live"
    assert publish(cms, pub, S2, "p2") == "live"
    text = open(ht).read()
    assert text.count("# BEGIN crtdh-publish-agent") == 1 and f"# Live release: {F2}." in text
    assert "ErrorDocument 404 /404.html" in text and "Header set X-Test yes" in text
    # owner adds a rule later; it survives the next publish and a rollback to the pre-agent site
    with open(ht, "a") as fh:
        fh.write("Header set X-Later yes\n")
    assert publish(cms, pub, S3, "p3") == "live"
    assert "X-Later" in open(ht).read()
    while not pub.rollback().startswith("legacy-"):
        pass
    text = open(ht).read()
    assert "crtdh-publish-agent" not in text
    assert "ErrorDocument 404 /404.html" in text and "X-Later" in text


# ------------------------------------------------------------------ LOW: redirects, already-live check
def test_cross_origin_redirect_refused(make_pub, cms, server):
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            seen.append(dict(self.headers))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"x")
    other = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=other.serve_forever, daemon=True).start()
    try:
        pub = make_pub()
        cms.queue(S1, "p1", make_build(S1, "p1"))
        cms.redirects["/api/v1/agent/builds/p1.tar.gz"] = f"http://127.0.0.1:{other.server_address[1]}/x"
        assert pub.run_once() == "failed"
        assert "another host" in cms.last("p1")["message"]
        assert seen == []  # nothing (and no signed header) reached the other host
    finally:
        other.shutdown()


def test_already_live_but_check_fails_is_not_reported_live(make_pub, cms, server):
    pub = make_pub()
    data = make_build(S1, "p1")
    cms.queue(S1, "p1", data)
    assert pub.run_once() == "live"
    cms.queue(S1, "p1", data)
    pub.web.override = lambda url: "<html>cached old page</html>"
    assert pub.run_once() == "failed"
    st = cms.last("p1")
    assert st["status"] == "failed" and st["step"] == "check_live"


# ------------------------------------------------------------------ A13: /_media/ vs the /media/ page
def test_media_page_is_site_content_and_hashes_go_to_underscore_media(make_pub, cms, server):
    pub = make_pub(keep_releases=1)
    img = b"P" * 64
    m = media_name(img, "avif")
    variant = m.replace(".avif", "-800.webp")
    pages = {"media/index.html": f'<meta name="crtdh-build" content="{S1}">gallery'}
    assert publish(cms, pub, S1, "p1", pages=pages, media={m: img, variant: b"V"}) == "live"
    assert "gallery" in live(pub, "media")
    root = server.home_path("public_html")
    assert os.path.exists(os.path.join(root, "_media", variant))
    mdir = server.home_path("crtdh-releases", "_media")
    with open(os.path.join(mdir, "0123456789abcdef.txt.bak"), "w") as fh:
        fh.write("does not match the GC pattern")
    pages2 = {"media/index.html": f'<meta name="crtdh-build" content="{S2}">gallery 2'}
    assert publish(cms, pub, S2, "p2", pages=pages2, media={}, media_all=[]) == "live"
    assert publish(cms, pub, S3, "p3", pages={"media/index.html": "gallery 3"}, media={}, media_all=[]) == "live"
    assert sorted(os.listdir(mdir)) == ["0123456789abcdef.txt.bak", "index.html"]  # hashes GC'd, other names kept
    assert "gallery 3" in live(pub, "media")


def test_media_name_must_match_contract(make_pub, cms, server):
    pub = make_pub()
    cms.queue(S1, "p1", make_build(S1, "p1", media={"banner.jpg": b"x"}))
    assert pub.run_once() == "failed"
    assert "bad media file name" in cms.last("p1")["message"]


def test_copy_strategy_keeps_shared_media(make_pub, cms, server):
    pub = make_pub(strategy="copy")
    img = b"C" * 40
    m = media_name(img)
    assert publish(cms, pub, S1, "p1", media={m: img}) == "live"
    assert publish(cms, pub, S2, "p2", media={}, media_all=[m]) == "live"
    assert os.path.exists(server.home_path("public_html", "_media", m))
    assert f"home {S2}" in live(pub)


def test_verify_job_unit():
    from publish_agent.cmsclient import BuildRejected, verify_job
    sha = "a" * 64
    good = Job("p", "s", "/x", sha, build_signature(SECRET, "p", "s", sha))
    verify_job(SECRET, good)
    for bad in ("", "zz" * 32, "A" * 64, "\u00e9" * 64):
        with pytest.raises(BuildRejected):
            verify_job(SECRET, Job("p", "s", "/x", sha, bad))


# ------------------------------------------------------------------ bandit B310 / B601 hardening
def test_shell_commands_are_fixed_templates_with_quoted_args():
    from publish_agent.remote import shell_command
    assert shell_command("probe") == "echo crtdh-shell-ok"
    assert shell_command("discover", web_root="/home/u/public_html") == "WEB_ROOT=/home/u/public_html sh -s"
    evil = "/x; rm -rf ~ #"
    assert shell_command("discover", web_root=evil) == "WEB_ROOT='/x; rm -rf ~ #' sh -s"
    with pytest.raises(KeyError):
        shell_command("rm -rf /")


def test_exec_sends_script_on_stdin_not_command_line():
    from publish_agent.remote import Remote
    calls = {}

    class Chan:
        def shutdown_write(self):
            calls["eof"] = True

        def recv_exit_status(self):
            return 0

    class Stream(io.BytesIO):
        channel = Chan()

    class Stdin:
        channel = Chan()

        def write(self, data):
            calls["stdin"] = data

    class Client:
        def exec_command(self, command, timeout=None):
            calls["command"] = command
            return Stdin(), Stream(b"ok"), Stream(b"")

    r = Remote.__new__(Remote)
    r.client = Client()
    assert r.exec("discover", stdin=b"echo hi\n", web_root="/w w") == (0, "ok")
    assert calls == {"command": "WEB_ROOT='/w w' sh -s", "stdin": b"echo hi\n", "eof": True}


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://site.example/", "gopher://x/"])
def test_live_check_only_fetches_http(url):
    from publish_agent.deploy import default_http_get
    with pytest.raises(ValueError, match="http"):
        default_http_get(url)


@pytest.mark.parametrize("url,ok", [
    ("", True), ("https://crtdh.iitkgp.in/", True), ("http://crtdh.iitkgp.in/", True),
    ("file:///var/www/index.html", False), ("crtdh.iitkgp.in", False),
])
def test_verify_url_must_be_http(make_cfg, url, ok):
    cfg = make_cfg()
    cfg.verify_url = url
    if ok:
        validate(cfg)
    else:
        with pytest.raises(ConfigError, match="verify_url"):
            validate(cfg)


# ------------------------------------------------------------------ _media/ never lists its files
@pytest.mark.parametrize("strategy", ["symlink", "htaccess", "copy"])
def test_media_folder_gets_an_empty_index_page(make_pub, cms, server, strategy):
    from publish_agent.deploy import MEDIA_INDEX

    pub = make_pub(strategy=strategy)
    img = b"I" * 48
    m = media_name(img)
    assert publish(cms, pub, S1, "p1", media={m: img}) == "live"
    found = [os.path.join(d, "index.html") for d, _dirs, files in os.walk(server.home_path())
             if os.path.basename(d) == "_media" and m in files]
    assert len(found) == 1, found  # the one shared media folder of this layout
    index = found[0]
    with open(index, "rb") as fh:
        body = fh.read()
    assert body == MEDIA_INDEX and m.encode() not in body and b"noindex" in body
    # kept through later publishes and media clean-up; rewritten if someone changes it
    with open(index, "wb") as fh:
        fh.write(b"tampered listing")
    assert publish(cms, pub, S2, "p2", media={}, media_all=[]) == "live"
    with open(index, "rb") as fh:
        assert fh.read() == MEDIA_INDEX
