"""Release metadata (file lists, media, build ids) is never inside a folder the web server serves."""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import pytest

from .conftest import SECRET
from .fakes import F1, F2, F3, F4, S1, S2, S3, S4, FakeSFTPServer, make_build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OLD_NAME = ".crtdh-release.json"


def publish(cms, pub, sid, pid, **kw):
    cms.queue(sid, pid, make_build(sid, pid, **kw))
    return pub.run_once()


def served_root(server, strategy):
    """The folder the web server maps / to (what Apache sees through the web-root link or .htaccess)."""
    return os.path.realpath(server.home_path("public_html"))


def all_files(root):
    for dirpath, _dirs, files in os.walk(root, followlinks=False):
        for f in files:
            yield os.path.join(dirpath, f)


@pytest.mark.parametrize("strategy", ["symlink", "htaccess", "swap", "copy"])
def test_metadata_lives_beside_releases_not_in_them(make_pub, cms, server, strategy):
    pub = make_pub(strategy=strategy, keep_releases=1)
    for sid, pid in ((S1, "p1"), (S2, "p2"), (S3, "p3"), (S4, "p4")):
        assert publish(cms, pub, sid, pid) == "live"
    home = server.home_path()
    assert not [p for p in all_files(home) if os.path.basename(p) == OLD_NAME]
    base = server.home_path("public_html", "_crtdh") if strategy == "htaccess" else server.home_path("crtdh-releases")
    meta_dir = os.path.join(base, "meta")
    # Pruned releases lose their metadata too: the live one plus keep_releases=1 older one remain.
    assert sorted(os.listdir(meta_dir)) == sorted([F3 + ".json", F4 + ".json"])
    meta = json.load(open(os.path.join(meta_dir, F4 + ".json")))
    assert meta["build_id"] == S4 and meta["files"]
    if strategy == "htaccess":
        # Inside the web root, but under _crtdh/, which the agent's rules refuse to serve directly.
        rules = open(server.home_path("public_html", ".htaccess")).read()
        assert "RewriteRule ^_crtdh(/|$) - [F,L]" in rules
    else:
        assert os.path.commonpath([os.path.realpath(meta_dir), served_root(server, strategy)]) \
            != served_root(server, strategy)


def test_swap_finds_the_live_release_without_a_marker_in_the_web_root(make_pub, cms, server):
    pub = make_pub(strategy="swap")
    assert publish(cms, pub, S1, "p1") == "live"
    assert publish(cms, pub, S2, "p2") == "live"
    state_path = server.home_path("crtdh-releases", "state.json")
    state = json.load(open(state_path))
    state["current"] = F1  # e.g. the PC died after the switch but before state.json was saved
    with open(state_path, "w") as fh:
        json.dump(state, fh)
    assert pub.status()["current"] == F2


# ---------------------------------------------------------------------------------------- through real Apache
def _apache():
    for binary, modules, mime in (
        ("apache2", "/usr/lib/apache2/modules", "/etc/mime.types"),
        ("httpd", "/usr/local/apache2/modules", "/usr/local/apache2/conf/mime.types"),
        ("httpd", "/usr/lib64/httpd/modules", "/etc/mime.types"),
        ("httpd", "/usr/lib/httpd/modules", "/etc/mime.types"),
    ):
        path = shutil.which(binary) or (f"/usr/sbin/{binary}" if os.path.exists(f"/usr/sbin/{binary}") else None)
        if path and os.path.isdir(modules) and os.path.exists(mime):
            return path, modules, mime
    return None


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def apache_server(client_key):
    """A fake SFTP account whose files a real Apache (deploy/staging/site/httpd.conf) serves."""
    found = _apache()
    if not found:
        pytest.skip("no Apache (apache2/httpd) on this machine")
    binary, modules, mime = found
    top = tempfile.mkdtemp(prefix="crtdh-apache-")
    os.chmod(top, 0o755)  # Apache's worker user must be able to walk in
    srv = FakeSFTPServer(os.path.join(top, "server"), client_key[0])
    os.makedirs(srv.home_path("public_html"))
    with open(srv.home_path("public_html", "index.html"), "w") as fh:
        fh.write("<html><body>old site</body></html>")
    for dirpath, dirs, files in os.walk(top):
        os.chmod(dirpath, 0o755)
    sroot = os.path.join(top, "apache")
    os.makedirs(os.path.join(sroot, "conf"))
    os.makedirs(os.path.join(sroot, "logs"))
    os.symlink(modules, os.path.join(sroot, "modules"))
    shutil.copy(mime, os.path.join(sroot, "conf", "mime.types"))
    port = _free_port()
    conf = open(os.path.join(REPO, "deploy", "staging", "site", "httpd.conf")).read()
    conf = (conf.replace('ServerRoot "/usr/local/apache2"', f'ServerRoot "{sroot}"')
                .replace("Listen 80\n", f"Listen 127.0.0.1:{port}\n")
                .replace("/srv/www", srv.home_path())
                .replace("ErrorLog /proc/self/fd/2", f"ErrorLog {sroot}/logs/error.log")
                .replace("CustomLog /proc/self/fd/1 cf", f"CustomLog {sroot}/logs/access.log cf"))
    conf += f'\nPidFile "{sroot}/logs/httpd.pid"\nMutex file:{sroot}/logs\n'
    conf_path = os.path.join(sroot, "conf", "httpd.conf")
    with open(conf_path, "w") as fh:
        fh.write(conf)
    env = dict(os.environ, SITE_HOST="crtdh.example")
    if os.geteuid() != 0:
        conf = conf.replace("User www-data\nGroup www-data\n", "")
        with open(conf_path, "w") as fh:
            fh.write(conf)
    check = subprocess.run([binary, "-f", conf_path, "-t"], env=env, capture_output=True, text=True)
    if check.returncode != 0:
        srv.close()
        shutil.rmtree(top, ignore_errors=True)
        pytest.skip(f"this Apache cannot load the staging config: {check.stderr.strip()[:200]}")
    proc = subprocess.Popen([binary, "-f", conf_path, "-DFOREGROUND"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield srv, base
    proc.terminate()
    proc.wait(timeout=10)
    srv.close()
    shutil.rmtree(top, ignore_errors=True)


def _status(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url), timeout=5).status
    except urllib.error.HTTPError as exc:
        return exc.code


@pytest.mark.parametrize("strategy", ["symlink", "htaccess"])
def test_apache_never_serves_release_metadata(apache_server, tmp_path, client_key, cms, strategy):
    from publish_agent.cmsclient import CMSClient
    from publish_agent.config import Config
    from publish_agent.deploy import Publisher
    from publish_agent.logutil import setup_logging
    from publish_agent.remote import Remote

    srv, base = apache_server
    kh = tmp_path / "known_hosts"
    kh.write_text(srv.known_hosts_line())
    cfg = Config(cms_url=cms.url, sftp_host="127.0.0.1", sftp_port=srv.port, sftp_user="u", key_file=client_key[1],
                 known_hosts=str(kh), web_root="~/public_html", strategy=strategy, keep_releases=2,
                 verify_url=base + "/", verify_attempts=2, verify_delay=0, state_dir=str(tmp_path / "state"),
                 log_file=str(tmp_path / "state" / "agent.log"))
    setup_logging(cfg.log_file, verbose=True)
    pub = Publisher(cfg, cms=CMSClient(cfg.cms_url, SECRET), connect=lambda: Remote.connect(cfg),
                    sleep=lambda s: None)
    for sid, pid in ((S1, "p1"), (S2, "p2")):
        cms.queue(sid, pid, make_build(sid, pid))
        assert pub.run_once() == "live"  # the agent's own live check went through Apache

    assert _status(base + "/") == 200
    assert _status(base + "/about/") == 200
    assert _status(base + "/" + OLD_NAME) == 404
    assert _status(base + "/.crtdh-staging.json") == 404
    if strategy == "htaccess":
        for path in (f"/_crtdh/meta/{F2}.json", "/_crtdh/state.json", f"/_crtdh/releases/{F2}/index.html",
                     "/_crtdh/meta/"):
            assert _status(base + path) == 403, path
    else:
        # The release store is beside the web root, so no URL reaches it at all.
        for path in (f"/crtdh-releases/meta/{F2}.json", "/crtdh-releases/state.json", f"/meta/{F2}.json"):
            assert _status(base + path) == 404, path
