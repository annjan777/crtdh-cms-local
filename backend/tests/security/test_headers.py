import pytest
from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db, pytest.mark.security]


@pytest.mark.parametrize("url", ["/api/v1/auth/csrf/", "/api/v1/auth/me/", "/api/v1/does-not-exist/"])
def test_security_headers_on_api_responses(url):
    r = APIClient().get(url)
    assert r["X-Frame-Options"] == "DENY"
    assert r["X-Content-Type-Options"] == "nosniff"
    assert r["Referrer-Policy"] == "same-origin"
    csp = r["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp and "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "camera=()" in r["Permissions-Policy"]
    assert r["X-Request-ID"]
    assert r["Cache-Control"] == "no-store"


def test_json_only_no_browsable_api():
    r = APIClient().get("/api/v1/auth/csrf/", HTTP_ACCEPT="text/html")
    assert r["Content-Type"].startswith("application/json") or r.status_code == 406


def test_unknown_api_path_is_plain_404_without_debug_page():
    r = APIClient().get("/api/v1/nope/")
    assert r.status_code == 404 and b"Traceback" not in r.content and b"urlpatterns" not in r.content


def test_hsts_sent_over_https(settings):
    r = APIClient().get("/api/v1/auth/csrf/", secure=True)
    assert r["Strict-Transport-Security"].startswith("max-age=31536000")


def test_cors_only_for_contact(settings):
    settings.CORS_ALLOWED_ORIGINS = ["https://crtdh.example.org"]
    c = APIClient()
    pre = c.options("/api/v1/contact/", HTTP_ORIGIN="https://crtdh.example.org", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")
    assert pre["Access-Control-Allow-Origin"] == "https://crtdh.example.org"
    assert "Access-Control-Allow-Credentials" not in pre
    other = c.options("/api/v1/auth/login/", HTTP_ORIGIN="https://crtdh.example.org", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")
    assert "Access-Control-Allow-Origin" not in other
    evil = c.options("/api/v1/contact/", HTTP_ORIGIN="https://evil.example", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")
    assert "Access-Control-Allow-Origin" not in evil
