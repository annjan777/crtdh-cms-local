import json
import os

import pytest

from publish_agent import strategies
from publish_agent.cmsclient import CMSClient, CMSError
from publish_agent.deploy import Publisher
from publish_agent.remote import Remote

from .conftest import SECRET
from .fakes import F1, F2, F3, S1, S2, S3, make_build, media_name

OLD = "old site"


def live_html(pub, path=""):
    return pub.web(f"https://crtdh.example/{path}")


def publish(cms, pub, sid, pid, **kw):
    cms.queue(sid, pid, make_build(sid, pid, **kw))
    return pub.run_once()


def read_log(pub):
    with open(pub.cfg.log_file, encoding="utf-8") as fh:
        return fh.read()


# ------------------------------------------------------------------ happy path + strategies
@pytest.mark.parametrize("strategy", ["symlink", "htaccess", "swap", "copy"])
def test_each_strategy_publish_and_rollback(make_pub, cms, server, strategy):
    pub = make_pub(strategy=strategy)
    img = b"A" * 500
    assert publish(cms, pub, S1, "p1", media={media_name(img): img}) == "live"
    assert cms.last("p1")["status"] == "live"
    assert f"home {S1}" in live_html(pub)
    assert f"about {S1}" in live_html(pub, "about")
    assert publish(cms, pub, S2, "p2") == "live"
    assert f"home {S2}" in live_html(pub)
    steps = [s["step"] for s in cms.statuses if s["publish_id"] == "p2"]
    assert steps == ["download", "upload", "switch", "check_live"]

    assert pub.rollback() == F1
    assert f"home {S1}" in live_html(pub)
    st = pub.status()
    assert st["current"] == F1 and st["strategy"] == strategy
    # A local backup of the pre-agent site was taken before the first switch.
    backups = os.listdir(os.path.join(pub.cfg.state_dir, "backups"))
    assert len(backups) == 1 and backups[0].endswith(".tar.gz")


@pytest.mark.parametrize("strategy", ["symlink", "htaccess", "swap"])
def test_rollback_to_pre_agent_site(make_pub, cms, server, strategy):
    pub = make_pub(strategy=strategy)
    assert publish(cms, pub, S1, "p1") == "live"
    target = pub.rollback()
    assert target.startswith("legacy-")
    assert OLD in live_html(pub)


def test_symlink_layout_and_media_link(make_pub, cms, server):
    pub = make_pub()
    img = b"IMG" * 50
    m = media_name(img)
    assert publish(cms, pub, S1, "p1", media={m: img}) == "live"
    root = server.home_path("public_html")
    assert os.path.islink(root)
    assert os.readlink(root) == f"crtdh-releases/releases/{F1}"  # relative: survives chroot
    assert os.path.islink(os.path.join(root, "_media"))
    assert open(os.path.join(root, "_media", m), "rb").read() == img
    legacy = [n for n in os.listdir(server.home_path("crtdh-releases", "releases")) if n.startswith("legacy-")]
    assert legacy and os.path.exists(server.home_path("crtdh-releases", "releases", legacy[0], "images", "logo.png"))


def test_htaccess_rules_shape(make_pub, cms, server):
    pub = make_pub(strategy="htaccess")
    assert publish(cms, pub, S1, "p1") == "live"
    text = open(server.home_path("public_html", ".htaccess")).read()
    assert f"# Live release: {F1}." in text
    assert "RewriteRule ^_media/(.+)$ _crtdh/_media/$1 [L]" in text
    assert f"RewriteRule ^(about)/?$ _crtdh/releases/{F1}/$1/index.html [L]" in text
    # Only FileInfo directives: an "Options" line is a 500 on hosts that allow AllowOverride FileInfo only.
    assert "Options" not in text
    # the old .htaccess (none here) is restorable and the old files are untouched
    assert os.path.exists(server.home_path("public_html", "images", "logo.png"))


def test_htaccess_strategy_carries_the_old_site_redirects(make_pub, cms, server):
    # The build's own .htaccess sends /about.html etc. to the new pages. In the htaccess strategy every request is
    # rewritten into releases/<id>/ first, so the agent repeats those redirects at the top level, before that.
    own = "\n".join([
        "<IfModule mod_alias.c>",
        "  RedirectMatch 301 ^/about\\.html$ /about/",
        "  RedirectMatch 301 ^/contact-us\\.html$ /contact/",
        "  RedirectMatch 410 ^/mail\\.php$",
        "  RedirectMatch 301 ^/(.*)$ https://elsewhere.example/",  # not the plain shape: never copied up
        "</IfModule>", ""])
    cms.queue(S1, "p1", make_build(S1, "p1", pages={".htaccess": own}))
    pub = make_pub(strategy="htaccess")
    assert pub.run_once() == "live"
    text = open(server.home_path("public_html", ".htaccess")).read()
    top = text.index("RewriteBase /")
    assert text.index("RewriteRule ^about\\.html$ /about/ [R=301,L]") > top
    assert "RewriteRule ^contact-us\\.html$ /contact/ [R=301,L]" in text
    assert "RewriteRule ^mail\\.php$ - [G,L]" in text
    assert "elsewhere.example" not in text
    # the redirects come before the catch-all that sends everything into the release
    assert text.index("RewriteRule ^about\\.html$") < text.index("RewriteRule ^(.*)$")


# ------------------------------------------------------------------ chaos
def test_resume_after_connection_drop_mid_upload(make_pub, cms, server):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    pages = {f"p{i}/index.html": f"page {i}" for i in range(12)}
    cms.queue(S2, "p2", make_build(S2, "p2", pages=pages))
    server.faults.files_opened = 0
    server.faults.drop_after_files = 6  # connection dies part-way through the site files
    assert pub.run_once() == "live"
    assert f"home {S2}" in live_html(pub)
    log = read_log(pub)
    assert "connection problem" in log
    assert "already there" in log  # second attempt resumed instead of starting over
    resumed = [line for line in log.splitlines() if "site files:" in line][-1]
    assert " 0 already there" not in resumed


def test_quota_full_fails_and_leaves_live_site(make_pub, cms, server):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    server.faults.written = 0
    server.faults.quota_bytes = 200  # disk full shortly after the upload starts
    big = {"big/index.html": "x" * 5000}
    assert publish(cms, pub, S2, "p2", pages=big) == "failed"
    st = cms.last("p2")
    assert st["status"] == "failed" and st["step"] == "upload"
    assert "quota" in st["message"].lower()
    server.faults.quota_bytes = None
    assert f"home {S1}" in live_html(pub)
    releases = os.listdir(server.home_path("crtdh-releases", "releases"))
    assert f"{F2}.partial" not in releases and F2 not in releases  # space freed again


def test_crash_between_upload_and_switch_then_same_publish_resumes(make_pub, cms, server, monkeypatch):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    real_switch = strategies.switch

    def crash(*a, **k):
        raise SystemExit("power cut")
    monkeypatch.setattr(strategies, "switch", crash)
    cms.queue(S2, "p2", make_build(S2, "p2"))
    with pytest.raises(SystemExit):
        pub.run_once()
    assert f"home {S1}" in live_html(pub)
    assert os.path.isdir(server.home_path("crtdh-releases", "releases", F2))

    monkeypatch.setattr(strategies, "switch", real_switch)
    server.faults.files_opened = 0
    assert pub.run_once() == "live"  # CMS re-offers p2: no re-upload, just the switch
    assert f"home {S2}" in live_html(pub)
    assert "already fully uploaded" in read_log(pub)


def test_crash_mid_upload_then_new_publish_cleans_staging(make_pub, cms, server, monkeypatch):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    calls = {"n": 0}
    real_put = Remote.put_file

    def dying_put(self, local, remote):
        calls["n"] += 1
        if calls["n"] == 2:
            raise SystemExit("agent killed")
        return real_put(self, local, remote)
    monkeypatch.setattr(Remote, "put_file", dying_put)
    cms.queue(S2, "p2", make_build(S2, "p2"))
    with pytest.raises(SystemExit):
        pub.run_once()
    monkeypatch.setattr(Remote, "put_file", real_put)
    rel = server.home_path("crtdh-releases", "releases")
    assert f"{F2}.partial" in os.listdir(rel)
    cms.jobs.clear()  # the CMS gave up on p2 and a newer publish arrives
    assert publish(cms, pub, S3, "p3") == "live"
    names = os.listdir(rel)
    assert f"{F2}.partial" not in names and F2 not in names
    assert f"home {S3}" in live_html(pub)


def test_retry_same_publish_id_is_idempotent(make_pub, cms, server):
    pub = make_pub()
    data = make_build(S1, "p1")
    cms.queue(S1, "p1", data)
    assert pub.run_once() == "live"
    cms.queue(S1, "p1", data)  # e.g. our "live" report was lost and the CMS asks again
    server.faults.files_opened = 0
    assert pub.run_once() == "live"
    assert server.faults.files_opened == 0  # nothing written on the server
    assert cms.last("p1")["status"] == "live"


def test_bad_signature_rejected(make_pub, cms, server):
    pub = make_pub()
    cms.queue(S1, "p1", make_build(S1, "p1"), tamper_sig=True)
    assert pub.run_once() == "failed"
    st = cms.last("p1")
    assert st["step"] == "verify" and "signature" in st["message"]
    assert not os.path.exists(server.home_path("crtdh-releases"))
    assert OLD in live_html(pub)


def test_sha_mismatch_rejected(make_pub, cms, server):
    pub = make_pub()
    cms.queue(S1, "p1", make_build(S1, "p1"), tamper_sha=True)
    assert pub.run_once() == "failed"
    assert "sha256" in cms.last("p1")["message"]
    assert OLD in live_html(pub)


def test_unsafe_tarball_rejected(make_pub, cms, server):
    import io
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("site/../../evil.txt")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    pub = make_pub()
    cms.queue(S1, "p1", buf.getvalue())
    assert pub.run_once() == "failed"
    assert "unsafe path" in cms.last("p1")["message"]


def test_missing_referenced_media_fails_before_switch(make_pub, cms, server):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    assert publish(cms, pub, S2, "p2", media_all=["0123456789abcdef.jpg"]) == "failed"
    assert "media" in cms.last("p2")["message"]
    assert f"home {S1}" in live_html(pub)


def test_live_check_failure_rolls_back(make_pub, cms, server):
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    pub.web.override = lambda url: '<meta name="crtdh-build" content="stale-cache">'
    assert publish(cms, pub, S2, "p2") == "failed"
    st = cms.last("p2")
    assert st["step"] == "check_live" and f"rolled back to {F1}" in st["message"]
    pub.web.override = None
    assert f"home {S1}" in live_html(pub)


def test_retention_and_media_gc(make_pub, cms, server):
    pub = make_pub(keep_releases=1)
    a, b, c = b"A" * 10, b"B" * 20, b"C" * 30
    ma, mb, mc = media_name(a), media_name(b), media_name(c)
    assert publish(cms, pub, S1, "p1", media={ma: a, mb: b}) == "live"
    media_dir = server.home_path("crtdh-releases", "_media")
    with open(os.path.join(media_dir, "keep-me.txt"), "w") as fh:
        fh.write("not ours")  # names that are not content hashes are never touched
    assert publish(cms, pub, S2, "p2", media={mc: c}, media_all=[mb, mc]) == "live"
    assert sorted(os.listdir(media_dir)) == sorted([ma, mb, mc, "keep-me.txt", "index.html"])  # s1 still kept
    assert publish(cms, pub, S3, "p3", media={}, media_all=[mc]) == "live"
    # kept: s3 (current) + s2 (1 previous) -> b and c referenced, a is garbage
    assert sorted(os.listdir(media_dir)) == sorted([mb, mc, "keep-me.txt", "index.html"])
    rel = os.listdir(server.home_path("crtdh-releases", "releases"))
    assert F1 not in rel and F2 in rel and F3 in rel
    assert any(n.startswith("legacy-") for n in rel)  # pre-agent site is never auto-deleted


def test_dry_run_changes_nothing(make_cfg, cms, server):
    cfg = make_cfg()
    from .fakes import FakeWeb
    pub = Publisher(cfg, cms=CMSClient(cfg.cms_url, SECRET), connect=lambda: Remote.connect(cfg),
                    http_get=FakeWeb(server), sleep=lambda s: None, dry_run=True)
    cms.queue(S1, "p1", make_build(S1, "p1"))
    before = sorted(os.listdir(server.home_path()))
    assert pub.run_once() == "dry-run"
    assert sorted(os.listdir(server.home_path())) == before
    assert cms.statuses == []
    assert not os.path.islink(server.home_path("public_html"))


def test_strategy_mismatch_is_refused(make_pub, make_cfg, cms, server):
    pub = make_pub(strategy="symlink")
    assert publish(cms, pub, S1, "p1") == "live"
    pub2 = make_pub(cfg=make_cfg(strategy="swap"))
    assert publish(cms, pub2, S2, "p2") == "failed"
    assert "set up for strategy 'symlink'" in cms.last("p2")["message"]


def test_auto_strategy_uses_discovery(make_pub, cms, server):
    pub = make_pub(strategy="auto")
    assert publish(cms, pub, S1, "p1") == "live"
    assert pub.local_state()["discovery"]["recommended"] == "symlink"
    assert os.path.islink(server.home_path("public_html"))


def test_wrong_secret_is_refused_by_cms(make_cfg, cms):
    cfg = make_cfg()
    with pytest.raises(CMSError, match="refused"):
        CMSClient(cfg.cms_url, "wrong-secret-value").next_job()
    assert cms.bad_auth == 1


def test_secrets_never_logged(make_pub, cms, server):
    from publish_agent.logutil import LOG, register_secret
    pub = make_pub()
    pw = "hunter2-sftp-password"
    register_secret(pw)
    assert publish(cms, pub, S1, "p1") == "live"
    cms.queue(S2, "p2", make_build(S2, "p2"), tamper_sig=True)
    pub.run_once()
    LOG.info("connecting with password=%s and secret %s", pw, SECRET)
    LOG.info("url https://user:%s@host/", pw)
    try:
        raise RuntimeError(f"boom {SECRET}")
    except RuntimeError:
        LOG.exception("failure")
    log = read_log(pub)
    assert SECRET not in log and pw not in log
    assert "***" in log
    local = open(pub.cfg.local_state_file).read()
    assert SECRET not in local and pw not in local
    assert SECRET not in json.dumps(cms.statuses)


def test_identical_requests_never_share_a_signature(make_cfg, cms, monkeypatch):
    import publish_agent.cmsclient as cc
    cfg = make_cfg()
    client = CMSClient(cfg.cms_url, SECRET)
    seen = []
    real = cc.sign_request

    def spy(*a, **k):
        h = real(*a, **k)
        seen.append(h["X-Agent-Signature"])
        return h
    monkeypatch.setattr(cc, "sign_request", spy)
    client.next_job()
    client.next_job()
    assert len(set(seen)) == 2


# ------------------------------------------------------------------ QA wave 2 D2: a build that never downloads
def test_failing_download_is_reported_failed_after_the_limit(make_pub, cms):
    pub = make_pub(max_download_errors=3)
    cms.queue(S1, "p1", make_build(S1, "p1"))
    del cms.builds["p1"]  # the CMS answers 404 for the tarball, every time
    for _ in range(2):
        with pytest.raises(CMSError):
            pub.run_once()
        assert cms.last("p1")["status"] == "uploading"
    assert pub.run_once() == "failed"
    last = cms.last("p1")
    assert last["status"] == "failed" and last["step"] == "download" and "after 3 attempts" in last["message"]
    assert pub.run_once() == "idle"  # no longer offered


def test_download_error_count_resets_on_success_and_per_publish(make_pub, cms):
    pub = make_pub(max_download_errors=2)
    data = make_build(S1, "p1")
    cms.queue(S1, "p1", data)
    del cms.builds["p1"]
    with pytest.raises(CMSError):
        pub.run_once()
    cms.builds["p1"] = data
    assert pub.run_once() == "live"
    cms.queue(S2, "p2", make_build(S2, "p2"))
    del cms.builds["p2"]
    with pytest.raises(CMSError):
        pub.run_once()  # first error for p2: p1's count does not carry over
    assert cms.last("p2")["status"] == "uploading"


# ------------------------------------------------------------------ QA wave 2 D4: ids with ':' (real ISO snapshot ids)
def test_real_snapshot_id_goes_live_and_rollback_confirms_it(make_pub, cms, server):
    assert ":" in S1 and F1 != S1  # the case that rolled every real publish back
    pub = make_pub()
    assert publish(cms, pub, S1, "p1") == "live"
    assert cms.last("p1")["status"] == "live"
    assert publish(cms, pub, S2, "p2") == "live"
    assert pub.rollback() == F1
    assert "live check did not confirm" not in read_log(pub)
