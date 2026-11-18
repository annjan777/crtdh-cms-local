import time

import pyotp
import pytest
from rest_framework.test import APIClient

from apps.accounts import mfa
from tests.support.factories import TEST_PASSWORD


@pytest.fixture(autouse=True)
def _fresh_cache():
    from django.core.cache import cache
    cache.clear()


class Browser:
    """An APIClient that behaves like the admin SPA: fetches the CSRF token, sends X-CSRFToken."""

    def __init__(self, ip="198.51.100.10"):
        self.c = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=ip)
        self.refresh_csrf()

    def refresh_csrf(self):
        self.token = self.c.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def post(self, url, data=None, **kw):
        return self.c.post(url, data or {}, format="json", HTTP_X_CSRFTOKEN=self.token, **kw)

    def get(self, url, **kw):
        return self.c.get(url, **kw)


def code_for(user, offset=0):
    user.refresh_from_db()
    secret = user.security.totp_secret
    step = int(time.time()) // 30 + offset
    return pyotp.TOTP(secret).at(step * 30)


def enrol(user):
    mfa.start_enrolment(user)
    user.refresh_from_db()
    assert mfa.confirm_enrolment(user, code_for(user, -1))
    user.security.refresh_from_db()  # step -1 used; steps 0 and +1 remain for sign-ins
    return user


def sign_in(browser, user, offset=1):
    r = browser.post("/api/v1/auth/login/", {"username": user.username, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.content
    r = browser.post("/api/v1/auth/mfa/", {"code": code_for(user, offset)})
    assert r.status_code == 200, r.content
    browser.token = r.json()["csrfToken"]
    return r


@pytest.fixture
def browser():
    return Browser()


@pytest.fixture
def api_as(api_as):
    """QA's api_as, with the CSRF token taken from GET /auth/csrf/'s body (the cookie is HttpOnly
    and named __Host-crtdh_csrf). Drop once the root harness reads the body token."""

    def make(who):
        client = api_as(who)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        client.credentials(HTTP_X_CSRFTOKEN=token)
        client.csrf_token = token
        return client

    return make
