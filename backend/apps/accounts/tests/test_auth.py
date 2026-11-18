import pytest
from django.contrib.auth.models import Group
from django.test import override_settings

from apps.accounts import mfa
from apps.accounts.models import AuthThrottle
from apps.accounts.signals import user_deactivated, user_sessions_revoked
from tests.support.errors import assert_contract_error
from tests.support.factories import TEST_PASSWORD

from .conftest import Browser, code_for, enrol, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def test_first_sign_in_enrols_mfa_then_signs_in(browser, editor):
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.json() == {"mfa_setup_required": True}
    assert browser.get("/api/v1/auth/me/").status_code == 401  # password alone is not a session
    r = browser.post("/api/v1/auth/mfa/enrol/")
    body = r.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/") and body["qr_data_uri"].startswith("data:image/svg+xml;base64,")
    assert body["qr_svg"].lstrip().startswith("<?xml") or "<svg" in body["qr_svg"][:200]
    assert "<script" not in body["qr_svg"]
    r = browser.post("/api/v1/auth/mfa/enrol/confirm/", {"code": code_for(editor)})
    assert r.status_code == 200, r.content
    data = r.json()
    assert len(data["recovery_codes"]) == 10 and data["roles"] == ["editor"] and data["mfa_enrolled"]
    browser.token = data["csrfToken"]
    me = browser.get("/api/v1/auth/me/").json()
    assert me["username"] == editor.username and me["roles"] == ["editor"]
    # recovery codes are stored hashed
    stored = list(editor.recovery_codes.values_list("code_hash", flat=True))
    assert not set(data["recovery_codes"]) & set(stored) and all(len(h) == 64 for h in stored)


def test_enrolled_user_cannot_re_enrol_from_password_step(browser, editor):
    enrol(editor)
    browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert browser.post("/api/v1/auth/mfa/enrol/").status_code == 403


def test_full_sign_in_and_cookie_flags(browser, editor):
    enrol(editor)
    r = sign_in(browser, editor)
    cookie = r.cookies["__Host-crtdh_session"]
    assert cookie["httponly"] and cookie["secure"] and cookie["samesite"] == "Strict" and cookie["path"] == "/"
    csrf = browser.c.cookies["__Host-crtdh_csrf"]
    assert csrf["httponly"] and csrf["secure"] and csrf["samesite"] == "Strict"
    assert browser.get("/api/v1/auth/me/").json()["mfa_enrolled"] is True


def test_session_key_rotates_on_sign_in(browser, editor):
    enrol(editor)
    browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    pre = browser.c.cookies["__Host-crtdh_session"].value
    browser.post("/api/v1/auth/mfa/", {"code": code_for(editor, 1)})
    assert browser.c.cookies["__Host-crtdh_session"].value != pre


def test_login_without_csrf_token_is_rejected(editor):
    from rest_framework.test import APIClient
    c = APIClient(enforce_csrf_checks=True)
    r = c.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD}, format="json")
    assert_contract_error(r, "CMS_CSRF_FAILED", status=403)


def test_unsafe_request_without_csrf_rejected_when_signed_in(browser, editor):
    enrol(editor)
    sign_in(browser, editor)
    r = browser.c.post("/api/v1/auth/logout/", {}, format="json")  # no X-CSRFToken
    assert r.status_code == 403


def test_wrong_password_is_401(browser, editor):
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": "wrong-password-123"})
    assert_contract_error(r, "CMS_UNAUTHENTICATED", status=401)
    r = browser.post("/api/v1/auth/login/", {"username": "nobody", "password": "wrong-password-123"})
    assert_contract_error(r, "CMS_UNAUTHENTICATED", status=401)  # same answer for unknown users


def test_user_lockout_with_backoff(browser, editor):
    for _ in range(5):
        browser.post("/api/v1/auth/login/", {"username": editor.username, "password": "nope-nope-nope"})
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.status_code == 429 and r.json()["code"] == "CMS_RATE_LIMITED"
    assert r.json()["locked_until"]  # contract addendum A6
    assert 0 < int(r.headers["Retry-After"]) <= 61
    # a different IP is still locked out for this username
    other = Browser(ip="198.51.100.99")
    assert other.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD}).status_code == 429
    # backoff doubles on the next failure
    t = AuthThrottle.objects.get(key=f"u:{editor.username}")
    from apps.accounts import lockout
    lockout.register_failure([t.key])
    assert 100 < lockout.retry_after([t.key]) <= 121


@override_settings(AUTH_LOCKOUT={"USER_THRESHOLD": 100, "IP_THRESHOLD": 3, "BASE_SECONDS": 60,
                                 "MAX_SECONDS": 3600, "RESET_AFTER_SECONDS": 86400})
def test_ip_lockout_across_usernames(browser, editor):
    for name in ("a1", "a2", "a3"):
        browser.post("/api/v1/auth/login/", {"username": name, "password": "nope-nope-nope"})
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.status_code == 429
    assert Browser(ip="203.0.113.50").post(
        "/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD}).status_code == 200


def test_wrong_mfa_code_counts_and_locks(browser, editor):
    enrol(editor)
    browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    for _ in range(5):
        assert browser.post("/api/v1/auth/mfa/", {"code": "000000"}).status_code in (401, 429)
    assert browser.post("/api/v1/auth/mfa/", {"code": code_for(editor, 1)}).status_code == 429


def test_totp_code_cannot_be_replayed(editor):
    enrol(editor)
    code = code_for(editor, 1)
    assert mfa.verify_code(editor, code)
    assert not mfa.verify_code(editor, code)


def test_recovery_code_works_once(browser, editor):
    enrol(editor)
    codes = mfa.regenerate_recovery_codes(editor)
    browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert browser.post("/api/v1/auth/mfa/", {"code": codes[0].upper()}).status_code == 200
    b2 = Browser()
    b2.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert b2.post("/api/v1/auth/mfa/", {"code": codes[0]}).status_code == 401


def test_mfa_step_without_password_step_is_401(browser, editor):
    enrol(editor)
    assert browser.post("/api/v1/auth/mfa/", {"code": code_for(editor)}).status_code == 401


def test_pending_step_expires(browser, editor, settings):
    enrol(editor)
    settings.MFA_PENDING_SECONDS = -1
    browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert browser.post("/api/v1/auth/mfa/", {"code": code_for(editor, 1)}).status_code == 401


def test_force_login_without_mfa_flag_is_not_a_cms_session(editor):
    from rest_framework.test import APIClient
    c = APIClient()
    c.force_login(editor)  # e.g. any other Django login path
    assert c.get("/api/v1/auth/me/").status_code == 401


def test_inactive_user_cannot_sign_in(browser, editor):
    enrol(editor)
    editor.is_active = False
    editor.save()
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.status_code == 401


def test_logout_ends_session(browser, editor):
    enrol(editor)
    sign_in(browser, editor)
    assert browser.post("/api/v1/auth/logout/").status_code == 204
    assert browser.get("/api/v1/auth/me/").status_code == 401


def test_revoke_all_signs_out_every_session(editor):
    enrol(editor)
    a, b = Browser(), Browser(ip="198.51.100.11")
    sign_in(a, editor, offset=0)
    sign_in(b, editor, offset=1)
    fired = []
    user_sessions_revoked.connect(lambda **kw: fired.append(kw["user"].pk), weak=False, dispatch_uid="t1")
    try:
        assert a.post("/api/v1/auth/sessions/revoke-all/").json()["revoked"] == 2
    finally:
        user_sessions_revoked.disconnect(dispatch_uid="t1")
    assert a.get("/api/v1/auth/me/").status_code == 401
    assert b.get("/api/v1/auth/me/").status_code == 401
    assert fired == [editor.pk]


def test_password_change_validates_and_ends_other_sessions(editor):
    enrol(editor)
    a, b = Browser(), Browser(ip="198.51.100.11")
    sign_in(a, editor, offset=0)
    sign_in(b, editor, offset=1)
    r = a.post("/api/v1/auth/password/", {"current_password": TEST_PASSWORD, "new_password": "short"})
    assert_contract_error(r, "CMS_VALIDATION", status=400, field="new_password")
    r = a.post("/api/v1/auth/password/", {"current_password": TEST_PASSWORD, "new_password": "a-much-longer-Passphrase-42"})
    assert r.status_code == 200, r.content
    a.token = r.json()["csrfToken"]
    assert a.get("/api/v1/auth/me/").status_code == 200
    assert b.get("/api/v1/auth/me/").status_code == 401


def test_no_bearer_token_endpoints():
    from rest_framework.test import APIClient
    for url in ("/api/v1/auth/token/", "/api/v1/auth/token/refresh/"):
        assert APIClient().post(url, {}).status_code in (403, 404)
    import importlib.util
    from django.conf import settings
    assert "rest_framework_simplejwt" not in settings.INSTALLED_APPS
    assert all("JWT" not in c for c in settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"])


def test_django_admin_not_routed():
    from rest_framework.test import APIClient
    assert APIClient().get("/admin/login/").status_code == 404


def test_password_validators_require_12_chars(settings):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        validate_password("Short1!abc")
    validate_password("correct-horse-battery-9")


def test_is_verified_helper(editor, rf):
    from django.contrib.sessions.backends.db import SessionStore
    req = rf.get("/")
    req.user, req.session = editor, SessionStore()
    assert not mfa.is_verified(req)
    mfa.mark_session_verified(req.session, editor)
    assert mfa.is_verified(req)


def test_process_upload_accepts_bytes():
    from apps.common.images import process_upload
    from tests.support.images import make_image_bytes
    assert process_upload(make_image_bytes(100, 80)).width == 100



def test_login_for_enrolled_user_says_mfa_required(browser, editor):
    enrol(editor)
    r = browser.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.json() == {"mfa_required": True}
