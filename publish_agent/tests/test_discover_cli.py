import os
import tarfile

import pytest

from publish_agent import agent
from publish_agent.config import ConfigError, load
from publish_agent.discover import backup_live_site, discover, format_report
from publish_agent.remote import Remote, RemoteError

from .conftest import SECRET
from .fakes import F1, F2, FakeWeb, S1, S2, make_build


def test_discovery_on_fake_host(make_cfg, server):
    cfg = make_cfg(strategy="auto")
    remote = Remote.connect(cfg)
    try:
        r = discover(cfg, remote, http_get=FakeWeb(server))
    finally:
        remote.close()
    assert r["web_root"] == "/home/u/public_html" and r["web_root_exists"]
    assert r["parent_writable"] and r["web_root_writable"]
    assert r["symlink_ok"] and r["rename_ok"] and r["posix_rename_ok"]
    assert r["shell"] is False  # SFTP-only account
    assert r["http"]["web_root_matches_url"] is True
    assert r["http"]["php"] is False and r["http"]["htaccess"] is False
    assert r["recommended"] == "symlink"
    # probes cleaned up after themselves
    assert not [n for n in os.listdir(server.home_path()) if "probe" in n]
    assert not [n for n in os.listdir(server.home_path("public_html")) if "probe" in n]
    assert "RECOMMENDED STRATEGY   : symlink" in format_report(r)


def test_discovery_falls_back_without_symlinks(make_cfg, server):
    server.faults.no_symlink = True
    cfg = make_cfg(strategy="auto")
    remote = Remote.connect(cfg)
    try:
        r = discover(cfg, remote, probe_http=False)
    finally:
        remote.close()
    assert r["symlink_ok"] is False
    assert r["recommended"] == "swap"


def test_backup_live_site(make_cfg, server):
    cfg = make_cfg()
    remote = Remote.connect(cfg)
    try:
        path = backup_live_site(cfg, remote, remote.abspath("~/public_html"))
    finally:
        remote.close()
    with tarfile.open(path) as tar:
        names = tar.getnames()
        assert "site/index.html" in names and "site/images/logo.png" in names
        assert tar.extractfile("site/images/logo.png").read() == b"PNGDATA"


def test_unknown_host_key_is_rejected(make_cfg, server):
    cfg = make_cfg()
    os.remove(cfg.known_hosts)
    with pytest.raises(RemoteError, match="trust-host-key"):
        Remote.connect(cfg)
    Remote.connect(cfg, trust_new_host_key=True).close()  # explicit first-time trust saves it
    assert "127.0.0.1" in open(cfg.known_hosts).read()
    Remote.connect(cfg).close()


def test_changed_host_key_is_refused(make_cfg, server):
    import paramiko
    cfg = make_cfg()
    other = paramiko.RSAKey.generate(1024)
    with open(cfg.known_hosts, "w") as fh:
        fh.write(f"[127.0.0.1]:{server.port} ssh-rsa {other.get_base64()}\n")
    with pytest.raises(RemoteError, match="CHANGED"):
        Remote.connect(cfg)


def test_password_auth_without_keyring_needs_interactive(make_cfg, server):
    cfg = make_cfg(key_file="", password_source="prompt")
    with pytest.raises(RemoteError, match="no SSH key"):
        Remote.connect(cfg)


# ------------------------------------------------------------------ config + CLI
def write_config(tmp_path, server, cms, client_key, extra=""):
    kh = tmp_path / "kh"
    kh.write_text(server.known_hosts_line())
    p = tmp_path / "config.ini"
    p.write_text(f"""
[cms]
url = {cms.url}
secret_env = CRTDH_TEST_SECRET
[sftp]
host = 127.0.0.1
port = {server.port}
user = u
key_file = {client_key[1]}
known_hosts = {kh}
[site]
web_root = ~/public_html
strategy = symlink
keep_releases = 2
[agent]
state_dir = {tmp_path / 'st'}
{extra}
""")
    return str(p)


def test_config_rejects_stored_password(tmp_path, server, cms, client_key):
    path = write_config(tmp_path, server, cms, client_key, extra="[x]\npassword = abc\n")
    with pytest.raises(ConfigError, match="Do not store passwords"):
        load(path)


def test_config_missing_secret_message(tmp_path, server, cms, client_key, monkeypatch):
    monkeypatch.delenv("CRTDH_TEST_SECRET", raising=False)
    cfg = load(write_config(tmp_path, server, cms, client_key))
    with pytest.raises(ConfigError, match="CRTDH_TEST_SECRET"):
        cfg.secret()


def test_cli_check_run_status_rollback(tmp_path, server, cms, client_key, monkeypatch, capsys):
    monkeypatch.setenv("CRTDH_TEST_SECRET", SECRET)
    path = write_config(tmp_path, server, cms, client_key)
    assert agent.main(["-c", path, "check", "--no-http"]) == 0
    out = capsys.readouterr().out
    assert "RECOMMENDED STRATEGY   : symlink" in out and "CMS connection         : ok" in out

    cms.queue(S1, "p1", make_build(S1, "p1"))
    assert agent.main(["-c", path, "--dry-run", "run", "--once"]) == 0
    assert not os.path.islink(server.home_path("public_html"))
    assert agent.main(["-c", path, "run", "--once"]) == 0
    assert agent.main(["-c", path, "run", "--once"]) == 0  # idle
    cms.queue(S2, "p2", make_build(S2, "p2"))
    assert agent.main(["-c", path, "run", "--once"]) == 0
    capsys.readouterr()
    assert agent.main(["-c", path, "status"]) == 0
    assert f'"current": "{F2}"' in capsys.readouterr().out
    assert agent.main(["-c", path, "rollback"]) == 0
    assert f"live release is now: {F1}" in capsys.readouterr().out
    assert os.readlink(server.home_path("public_html")).endswith("/" + F1)
    log = open(tmp_path / "st" / "logs" / "agent.log").read()
    assert SECRET not in log


def test_cli_bad_config_exit_code(tmp_path, capsys):
    assert agent.main(["-c", str(tmp_path / "missing.ini"), "status"]) == 2
    assert "config file not found" in capsys.readouterr().err


def test_single_instance_lock(tmp_path):
    lock = str(tmp_path / "a.lock")
    with agent.SingleInstance(lock):
        with pytest.raises(SystemExit, match="already running"):
            with agent.SingleInstance(lock):
                pass


def test_keygen_key_logs_in(tmp_path, make_cfg):
    import paramiko
    from .fakes import FakeSFTPServer
    path = str(tmp_path / "keys" / "k")
    assert agent.main(["keygen", path]) == 0
    assert agent.main(["keygen", path]) == 1  # never overwrites
    key = paramiko.Ed25519Key(filename=path)
    assert open(path + ".pub").read().startswith("ssh-ed25519 " + key.get_base64())
    srv = FakeSFTPServer(str(tmp_path / "srv2"), key)
    try:
        cfg = make_cfg(key_file=path, sftp_port=srv.port)
        with open(cfg.known_hosts, "w") as fh:
            fh.write(srv.known_hosts_line())
        r = Remote.connect(cfg)
        assert r.home == "/home/u"
        r.close()
    finally:
        srv.close()


def test_example_config_loads(tmp_path, monkeypatch):
    import shutil
    src = os.path.join(os.path.dirname(__file__), "..", "config.example.ini")
    dst = tmp_path / "config.ini"
    text = open(src).read().replace("user = CHANGE_ME", "user = crtdh").replace("key_file = keys/crtdh_publish_ed25519", "key_file =")
    dst.write_text(text)
    (tmp_path / "agent-secret.txt").write_text("from-file-secret\n")
    cfg = load(str(dst))
    assert cfg.secret() == "from-file-secret"
    assert cfg.strategy == "auto" and cfg.keep_releases == 3
    assert cfg.state_dir == str(tmp_path / "state")
    del shutil


# ---------------------------------------------------------------- Cloudflare Access service token (GO-LIVE blocker 2)
ACCESS_ID = "0123456789abcdef0123456789abcdef.access"
ACCESS_SECRET = "cf-access-test-secret-0123456789abcdef0123456789"


def test_config_refuses_an_inline_access_secret(tmp_path, server, cms, client_key):
    path = write_config(tmp_path, server, cms, client_key)
    _add_to_cms_section(path, f"access_client_id = {ACCESS_ID}\naccess_client_secret = {ACCESS_SECRET}")
    with pytest.raises(ConfigError, match="Do not store passwords or secrets"):
        load(path)


def _add_to_cms_section(path, line):
    text = open(path).read().replace("[cms]\n", f"[cms]\n{line}\n")
    with open(path, "w") as fh:
        fh.write(text)


def test_access_secret_from_file_or_env_and_missing_secret_is_an_error(tmp_path, server, cms, client_key, monkeypatch):
    path = write_config(tmp_path, server, cms, client_key)
    _add_to_cms_section(path, f"access_client_id = {ACCESS_ID}")
    monkeypatch.delenv("CRTDH_CF_ACCESS_SECRET", raising=False)
    with pytest.raises(ConfigError, match="CRTDH_CF_ACCESS_SECRET"):
        load(path).access_headers()
    monkeypatch.setenv("CRTDH_CF_ACCESS_SECRET", ACCESS_SECRET)
    assert load(path).access_headers() == {"CF-Access-Client-Id": ACCESS_ID, "CF-Access-Client-Secret": ACCESS_SECRET}
    (tmp_path / "access-secret.txt").write_text("from-file\n")
    _add_to_cms_section(path, "access_secret_file = access-secret.txt")
    assert load(path).access_headers()["CF-Access-Client-Secret"] == "from-file"
    # no id configured: nothing is sent (installations without Access keep working)
    plain = tmp_path / "plain"
    plain.mkdir()
    assert load(write_config(plain, server, cms, client_key)).access_headers() == {}


def test_access_headers_on_every_cms_request_and_never_logged(make_cfg, cms, server):
    from publish_agent.cmsclient import CMSClient
    from publish_agent.deploy import Publisher
    from publish_agent.remote import Remote

    from .conftest import SECRET
    cms.require_access = {"CF-Access-Client-Id": ACCESS_ID, "CF-Access-Client-Secret": ACCESS_SECRET}
    cfg = make_cfg()
    pub = Publisher(cfg, cms=CMSClient(cfg.cms_url, SECRET, access_headers=dict(cms.require_access)),
                    connect=lambda: Remote.connect(cfg), http_get=FakeWeb(server), sleep=lambda s: None)
    cms.queue(S1, "p1", make_build(S1, "p1"))
    assert pub.run_once() == "live"
    methods = {(m, p.split("?")[0].rsplit("/", 1)[0]) for m, p, _ in cms.requests}
    assert ("GET", "/api/v1/agent/next") in methods and ("POST", "/api/v1/agent/status") in methods
    assert any("/builds/" in p for _, p, _ in cms.requests)
    for _, _, headers in cms.requests:
        headers = {k.lower(): v for k, v in headers.items()}
        assert headers.get("cf-access-client-id") == ACCESS_ID and headers.get("cf-access-client-secret") == ACCESS_SECRET
    with open(cfg.log_file, encoding="utf-8") as fh:
        assert ACCESS_SECRET not in fh.read()


def test_missing_access_token_gets_a_clear_message(make_cfg, cms):
    from publish_agent.cmsclient import CMSClient, CMSError

    from .conftest import SECRET
    cms.require_access = {"CF-Access-Client-Id": ACCESS_ID, "CF-Access-Client-Secret": ACCESS_SECRET}
    cfg = make_cfg()
    with pytest.raises(CMSError, match="Cloudflare Access sent the agent to its sign-in page"):
        CMSClient(cfg.cms_url, SECRET).next_job()
