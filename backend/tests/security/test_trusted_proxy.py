"""Only the gateway/cloudflared may set forwarding headers or (in production) talk to the app at all."""
import pytest
from django.test import Client

from apps.common.middleware import peer_is_trusted
from config.security import production_problems

pytestmark = [pytest.mark.django_db, pytest.mark.security]
GATEWAY, TUNNEL, STRANGER = "172.30.80.10", "172.30.80.11", "172.30.81.7"


@pytest.fixture
def proxies(settings):
    settings.TRUSTED_PROXY_IPS = [GATEWAY, TUNNEL]
    settings.TRUST_CF_CONNECTING_IP = True
    return settings


def test_peer_is_trusted(proxies):
    assert peer_is_trusted(GATEWAY) and peer_is_trusted(TUNNEL)
    assert not peer_is_trusted(STRANGER) and not peer_is_trusted("") and not peer_is_trusted("garbage")


def test_direct_peer_refused_when_proxy_required(proxies):
    proxies.REQUIRE_TRUSTED_PROXY = True
    r = Client(REMOTE_ADDR=STRANGER).get("/api/v1/auth/csrf/", HTTP_CF_CONNECTING_IP="198.51.100.1")
    assert r.status_code == 403
    assert Client(REMOTE_ADDR=STRANGER).get("/cms/login").status_code == 403
    assert Client(REMOTE_ADDR=GATEWAY).get("/api/v1/auth/csrf/").status_code == 200


def test_forwarding_headers_stripped_from_untrusted_peer(proxies, settings):
    from django.http import JsonResponse
    from django.urls import path

    seen = {}

    def probe(request):
        from apps.common.middleware import client_ip
        seen.update(ip=client_ip(request), secure=request.is_secure(),
                    cf=request.META.get("HTTP_CF_CONNECTING_IP"))
        return JsonResponse({})

    import config.urls as root
    settings.ROOT_URLCONF = type("U", (), {"urlpatterns": root.urlpatterns + [path("probe/", probe)]})
    settings.SECURE_SSL_REDIRECT = False
    Client(REMOTE_ADDR=STRANGER).get("/probe/", HTTP_CF_CONNECTING_IP="198.51.100.9", HTTP_X_FORWARDED_PROTO="https")
    assert seen == {"ip": STRANGER, "secure": False, "cf": None}
    Client(REMOTE_ADDR=GATEWAY).get("/probe/", HTTP_CF_CONNECTING_IP="198.51.100.9", HTTP_X_FORWARDED_PROTO="https")
    assert seen == {"ip": "198.51.100.9", "secure": True, "cf": "198.51.100.9"}


def test_login_lockout_not_dodged_by_spoofed_cf_header(proxies, editor):
    from rest_framework.test import APIClient
    c = APIClient(REMOTE_ADDR=STRANGER)
    for i in range(25):
        c.post("/api/v1/auth/login/", {"username": f"nobody{i}", "password": "x"}, format="json",
               HTTP_CF_CONNECTING_IP=f"198.51.100.{i}")
    r = c.post("/api/v1/auth/login/", {"username": "someone", "password": "x"}, format="json",
               HTTP_CF_CONNECTING_IP="198.51.100.200")
    assert r.status_code == 429  # IP lockout/throttle keyed on the real peer


BASE = dict(debug=False, env_name="production", secret_key="k" * 30 + "abcdefghijklmnopqrstuvwxyz", allowed_hosts=["x"],
            cors_allow_all=False, cors_origins=[], csrf_trusted_origins=[],
            database_engine="django.db.backends.postgresql", allow_sqlite=False, django_admin_enabled=False)


def test_production_requires_proxy_list_when_trusting_headers():
    assert production_problems(**BASE) == []
    assert production_problems(**BASE, trust_cf_connecting_ip=True)
    assert production_problems(**BASE, require_trusted_proxy=True)
    assert production_problems(**BASE, trust_cf_connecting_ip=True, require_trusted_proxy=True,
                               trusted_proxy_ips=[GATEWAY, TUNNEL]) == []
    assert production_problems(**BASE, trusted_proxy_ips=["0.0.0.0/0"])
    assert production_problems(**BASE, trusted_proxy_ips=["not-an-ip"])
