"""academicweb mode (deploy/academicweb): Apache on the same host proxies /cms/ and /api/ to the app.

Apache's mod_proxy appends the client to X-Forwarded-For and sends no X-Forwarded-Proto, so for the local peer
only, the last X-Forwarded-For entry is the client and a missing proto counts as https. The admin SPA is served
under /cms/ with the gateway's own CSP.
"""
import pytest
from django.test import Client

from apps.common.middleware import client_ip

pytestmark = [pytest.mark.django_db, pytest.mark.security]
LOCAL, STRANGER = "127.0.0.1", "198.51.100.9"


@pytest.fixture
def shared_host(settings, tmp_path):
    settings.TRUSTED_PROXY_IPS = [LOCAL]
    settings.TRUST_X_FORWARDED_FOR = True
    settings.FORWARDED_PROTO_DEFAULT = "https"
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>admin</html>")
    (dist / "preview.html").write_text("<html>preview</html>")
    (dist / "assets" / "main-abc.js").write_text("console.log(1)")
    settings.ADMIN_DIST_DIR = str(dist)
    return settings


def _probe(settings, **meta):
    from django.test import RequestFactory

    from apps.common.middleware import TrustedProxyMiddleware

    req = RequestFactory().get("/x", **meta)
    seen = {}

    def view(r):
        seen.update(ip=client_ip(r), secure=r.is_secure())
        return None

    TrustedProxyMiddleware(view)(req)
    return seen


def test_last_forwarded_for_entry_is_the_client_for_the_local_proxy_only(shared_host):
    # The client sent a fake first entry; Apache appended the real address last.
    assert _probe(shared_host, REMOTE_ADDR=LOCAL, HTTP_X_FORWARDED_FOR="10.0.0.1, 203.0.113.5")["ip"] == "203.0.113.5"
    assert _probe(shared_host, REMOTE_ADDR=STRANGER, HTTP_X_FORWARDED_FOR="203.0.113.5")["ip"] == STRANGER
    assert _probe(shared_host, REMOTE_ADDR=LOCAL, HTTP_X_FORWARDED_FOR="not-an-ip")["ip"] == LOCAL


def test_missing_proto_counts_as_https_only_from_the_local_proxy(shared_host):
    assert _probe(shared_host, REMOTE_ADDR=LOCAL)["secure"] is True
    assert _probe(shared_host, REMOTE_ADDR=LOCAL, HTTP_X_FORWARDED_PROTO="http")["secure"] is False
    assert _probe(shared_host, REMOTE_ADDR=STRANGER)["secure"] is False


def test_admin_app_serves_screens_assets_and_headers(shared_host):
    c = Client(REMOTE_ADDR=LOCAL)
    for path in ("/cms/", "/cms/pages/home", "/cms/review"):
        r = c.get(path)
        assert r.status_code == 200 and b"admin" in b"".join(r.streaming_content), path
        assert "frame-ancestors 'none'" in r["Content-Security-Policy"] and r["X-Frame-Options"] == "DENY"
        assert r["Cache-Control"] == "no-cache"
    p = c.get("/cms/preview.html")
    assert p.status_code == 200 and "frame-ancestors 'self'" in p["Content-Security-Policy"]
    assert p["X-Frame-Options"] == "SAMEORIGIN"
    a = c.get("/cms/assets/main-abc.js")
    assert a.status_code == 200 and "immutable" in a["Cache-Control"]
    assert c.get("/cms/assets/missing.js").status_code == 404  # never the app shell for a missing file
    assert c.get("/cms/../config/settings.py").status_code == 404
    assert c.get("/cms/%2e%2e/%2e%2e/etc/passwd").status_code == 404
    assert c.post("/cms/pages/home").status_code == 405
    assert c.get("/cms")["Location"] == "/cms/"


def test_admin_app_off_without_dist(settings):
    settings.ADMIN_DIST_DIR = ""
    assert Client().get("/cms/pages/home").status_code == 404
