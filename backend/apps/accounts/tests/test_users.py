import pytest
from django.contrib.auth import get_user_model

from apps.accounts.signals import user_deactivated
from tests.support.errors import assert_contract_error

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


def test_unknown_user_is_404(api_as):
    assert_contract_error(api_as("admin").post("/api/v1/auth/users/999999/deactivate/", format="json"),
                          "CMS_NOT_FOUND", status=404)
