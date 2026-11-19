"""MFA_ENABLED=False (the default outside tests): password alone signs in, MFA is hidden everywhere."""
import pytest
from django.test import override_settings

from tests.support.factories import TEST_PASSWORD

from .conftest import enrol

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mfa_off")]

MFA_URLS = ["/api/v1/auth/mfa/", "/api/v1/auth/mfa/enrol/", "/api/v1/auth/mfa/enrol/confirm/"]


@pytest.fixture
def mfa_off():
    with override_settings(MFA_ENABLED=False):
        yield


def _login(browser, user, password=TEST_PASSWORD):
    return browser.post("/api/v1/auth/login/", {"username": user.username, "password": password})


def test_password_alone_signs_in(browser, editor):
    res = _login(browser, editor)
    assert res.status_code == 200, res.content
    body = res.json()
    assert body["username"] == editor.username and body["mfa_enabled"] is False
    assert "mfa_required" not in body and "mfa_setup_required" not in body
    browser.token = body["csrfToken"]
    me = browser.get("/api/v1/auth/me/")
    assert me.status_code == 200 and me.json()["username"] == editor.username


def test_already_enrolled_user_is_not_asked_for_a_code(browser, editor):
    with override_settings(MFA_ENABLED=True):
        enrol(editor)
    res = _login(browser, editor)
    assert res.status_code == 200 and res.json()["mfa_enrolled"] is False


def test_wrong_password_still_refused(browser, editor):
    assert _login(browser, editor, "not-the-password").status_code == 401


@pytest.mark.parametrize("url", MFA_URLS)
def test_mfa_endpoints_answer_404(browser, editor, url):
    assert browser.post(url, {"code": "123456"}).status_code == 404


def test_signed_in_mfa_actions_answer_404(browser, cms_admin, editor):
    browser.token = _login(browser, cms_admin).json()["csrfToken"]
    assert browser.post("/api/v1/auth/mfa/recovery-codes/", {"code": "123456"}).status_code == 404
    assert browser.post(f"/api/v1/auth/users/{editor.pk}/reset-mfa/").status_code == 404
