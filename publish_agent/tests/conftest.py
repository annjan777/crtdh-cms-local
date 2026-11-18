import os
import sys

import paramiko
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from publish_agent.cmsclient import CMSClient  # noqa: E402
from publish_agent.config import Config  # noqa: E402
from publish_agent.deploy import Publisher  # noqa: E402
from publish_agent.logutil import setup_logging  # noqa: E402
from publish_agent.remote import Remote  # noqa: E402

from .fakes import FakeCMS, FakeSFTPServer, FakeWeb  # noqa: E402

SECRET = "local-test-agent-secret-0123456789"


@pytest.fixture(scope="session")
def client_key(tmp_path_factory):
    key = paramiko.RSAKey.generate(2048)
    path = tmp_path_factory.mktemp("keys") / "id_rsa"
    key.write_private_key_file(str(path))
    return key, str(path)


@pytest.fixture
def server(tmp_path, client_key):
    srv = FakeSFTPServer(str(tmp_path / "server"), client_key[0])
    os.makedirs(srv.home_path("public_html"))
    with open(srv.home_path("public_html", "index.html"), "w") as fh:
        fh.write("<html><body>old site</body></html>")
    os.makedirs(srv.home_path("public_html", "images"))
    with open(srv.home_path("public_html", "images", "logo.png"), "wb") as fh:
        fh.write(b"PNGDATA")
    yield srv
    srv.close()


@pytest.fixture
def cms():
    c = FakeCMS(SECRET)
    yield c
    c.close()


@pytest.fixture
def make_cfg(tmp_path, server, client_key, cms):
    def _make(**over):
        state = tmp_path / "agent-state"
        state.mkdir(exist_ok=True)
        kh = state / "known_hosts"
        kh.write_text(server.known_hosts_line())
        cfg = Config(cms_url=cms.url, sftp_host="127.0.0.1", sftp_port=server.port, sftp_user="u",
                     key_file=client_key[1], known_hosts=str(kh), web_root="~/public_html",
                     strategy="symlink", keep_releases=2, verify_url="https://crtdh.example/",
                     verify_attempts=2, verify_delay=0, state_dir=str(state),
                     log_file=str(state / "logs" / "agent.log"))
        for k, v in over.items():
            setattr(cfg, k, v)
        setup_logging(cfg.log_file, verbose=True)
        return cfg
    return _make


@pytest.fixture
def make_pub(make_cfg, server, cms):
    def _make(cfg=None, **over):
        cfg = cfg or make_cfg(**over)
        web = FakeWeb(server)
        pub = Publisher(cfg, cms=CMSClient(cfg.cms_url, SECRET), connect=lambda: Remote.connect(cfg),
                        http_get=web, sleep=lambda s: None)
        pub.web = web
        return pub
    return _make
