import pytest
from django.contrib.auth import get_user_model

from apps.accounts.signals import user_deactivated
from tests.support.errors import assert_contract_error

from tests.support.factories import TEST_PASSWORD

from .conftest import Browser, enrol, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.security]
User = get_user_model()


@pytest.mark.parametrize("role,expected", [(None, 401), ("editor", 403), ("publisher", 403), ("admin", 200)])
def test_user_list_is_admin_only(api_as, role, expected):
    assert api_as(role).get("/api/v1/auth/users/").status_code == expected


def test_admin_creates_user_with_one_time_password(api_as):
    r = api_as("admin").post("/api/v1/auth/users/", {"username": "new.editor", "email": "n@example.test",
                                                    "role": "editor"}, format="json")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["roles"] == ["editor"] and body["must_change_password"] and len(body["temporary_password"]) >= 20
    u = User.objects.get(username="new.editor")
    assert u.check_password(body["temporary_password"]) and not u.is_staff and not u.is_superuser
    listed = api_as("admin").get("/api/v1/auth/users/").json()["results"]
    assert all("temporary_password" not in x and "password" not in x for x in listed)


def test_create_rejects_bad_role_and_duplicate(api_as, editor):
    c = api_as("admin")
    r = c.post("/api/v1/auth/users/", {"username": "x_y", "email": "x@example.test", "role": "superuser"}, format="json")
    assert_contract_error(r, "CMS_VALIDATION", status=400, field="role")
    r = c.post("/api/v1/auth/users/", {"username": editor.username.upper(), "email": "x@example.test", "role": "editor"}, format="json")
    assert_contract_error(r, "CMS_VALIDATION", status=400, field="username")


def test_set_role(api_as, editor):
    r = api_as("admin").post(f"/api/v1/auth/users/{editor.pk}/role/", {"role": "publisher"}, format="json")
    assert r.json()["roles"] == ["editor", "publisher"]
    assert list(editor.groups.values_list("name", flat=True)) == ["publisher"]


def test_editor_cannot_promote_self(api_as, editor):
    c = api_as(editor)
    assert c.post(f"/api/v1/auth/users/{editor.pk}/role/", {"role": "admin"}, format="json").status_code == 403


def test_deactivate_kills_sessions_and_signals(api_as, editor):
    enrol(editor)
    victim = Browser()
    sign_in(victim, editor)
    seen = []
    user_deactivated.connect(lambda **kw: seen.append(kw["user"].pk), weak=False, dispatch_uid="t2")
    try:
        r = api_as("admin").post(f"/api/v1/auth/users/{editor.pk}/deactivate/", format="json")
    finally:
        user_deactivated.disconnect(dispatch_uid="t2")
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert seen == [editor.pk]
    assert victim.get("/api/v1/auth/me/").status_code == 401


def test_last_admin_is_protected(api_as, cms_admin):
    c = api_as(cms_admin)
    r = c.post(f"/api/v1/auth/users/{cms_admin.pk}/deactivate/", format="json")
    assert_contract_error(r, "CMS_VALIDATION", status=400)
    r = c.post(f"/api/v1/auth/users/{cms_admin.pk}/role/", {"role": "editor"}, format="json")
    assert_contract_error(r, "CMS_VALIDATION", status=400)


def test_reset_mfa_signs_user_out_and_requires_enrolment(api_as, editor):
    enrol(editor)
    b = Browser()
    sign_in(b, editor)
    r = api_as("admin").post(f"/api/v1/auth/users/{editor.pk}/reset-mfa/", format="json")
    assert r.json()["mfa_enrolled"] is False
    assert b.get("/api/v1/auth/me/").status_code == 401


def test_reset_mfa_replaces_password_so_old_password_cannot_enrol(api_as, editor):
    """Review finding: with the old password kept, whoever knows it enrols the new TOTP."""
    enrol(editor)
    r = api_as("admin").post(f"/api/v1/auth/users/{editor.pk}/reset-mfa/", format="json")
    temp = r.json()["temporary_password"]
    assert r.json()["must_change_password"] is True
    attacker = Browser(ip="203.0.113.5")
    r = attacker.post("/api/v1/auth/login/", {"username": editor.username, "password": TEST_PASSWORD})
    assert r.status_code == 401
    assert attacker.post("/api/v1/auth/mfa/enrol/").status_code == 401
    owner = Browser(ip="198.51.100.20")
    assert owner.post("/api/v1/auth/login/", {"username": editor.username, "password": temp}).json() == {
        "mfa_setup_required": True}


def test_admin_cannot_reset_own_mfa(api_as, cms_admin):
    r = api_as(cms_admin).post(f"/api/v1/auth/users/{cms_admin.pk}/reset-mfa/", format="json")
    assert r.status_code == 400


def test_unknown_user_is_404(api_as):
    assert_contract_error(api_as("admin").post("/api/v1/auth/users/999999/deactivate/", format="json"),
                          "CMS_NOT_FOUND", status=404)


def test_temporary_password_must_be_changed_before_anything_else(api_as):
    from tests.support.factories import TEST_PASSWORD  # noqa: F401
    admin = api_as("admin")
    body = admin.post("/api/v1/auth/users/", {"username": "temp.user", "email": "t@example.test", "role": "editor"},
                      format="json").json()
    user = User.objects.get(username="temp.user")
    enrol(user)
    b = Browser()
    b.post("/api/v1/auth/login/", {"username": "temp.user", "password": body["temporary_password"]})
    r = b.post("/api/v1/auth/mfa/", {"code": __import__("apps.accounts.tests.conftest", fromlist=["x"]).code_for(user, 1)})
    b.token = r.json()["csrfToken"]
    assert b.get("/api/v1/auth/me/").json()["must_change_password"] is True
    assert_contract_error(b.get("/api/v1/hero-slides/"), "CMS_FORBIDDEN_ROLE", status=403)
    r = b.post("/api/v1/auth/password/", {"current_password": body["temporary_password"],
                                          "new_password": "my-own-long-passphrase-7"})
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    b.token = r.json()["csrfToken"]
    assert b.get("/api/v1/hero-slides/").status_code != 403


def test_admin_password_reset(api_as, editor):
    enrol(editor)
    victim = Browser()
    sign_in(victim, editor)
    r = api_as("admin").post(f"/api/v1/auth/users/{editor.pk}/reset-password/", format="json")
    assert r.status_code == 200 and r.json()["must_change_password"] and r.json()["temporary_password"]
    assert victim.get("/api/v1/auth/me/").status_code == 401
    editor.refresh_from_db()
    assert editor.check_password(r.json()["temporary_password"])


def test_clear_auth_throttles():
    from datetime import timedelta
    from django.core.management import call_command
    from django.utils import timezone
    from apps.accounts.models import AuthThrottle
    AuthThrottle.objects.create(key="u:old", failures=3)
    AuthThrottle.objects.create(key="u:new", failures=3)
    AuthThrottle.objects.filter(key="u:old").update(updated_at=timezone.now() - timedelta(days=2))
    call_command("clear_auth_throttles")
    assert list(AuthThrottle.objects.values_list("key", flat=True)) == ["u:new"]
