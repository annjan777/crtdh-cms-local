from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.roles import user_roles

pytestmark = pytest.mark.django_db
User = get_user_model()


def run(*args):
    out = StringIO()
    call_command("cms_users", *args, stdout=out)
    return out.getvalue()


def test_lists_each_user_with_top_role():
    ed = User.objects.create_user("ed")
    ed.groups.add(Group.objects.get_or_create(name="editor")[0])
    User.objects.create_user("off", is_active=False)
    User.objects.create_superuser("root", password="x-not-used-9")
    out = run()
    lines = {line.split()[0]: line for line in out.splitlines()}
    assert "editor" in lines["ed"]
    assert "admin" in lines["root"] and "superuser" in lines["root"]
    assert "cannot sign in" in lines["off"]


def test_make_admin_gives_admin_role_and_switches_user_on():
    u = User.objects.create_user("Annjan.Test", is_active=False)
    out = run("--make-admin", "annjan.test")
    u.refresh_from_db()
    assert u.is_active and user_roles(u)[-1] == "admin"
    assert "now has the admin role" in out


def test_make_admin_unknown_user_fails_clearly():
    with pytest.raises(CommandError, match="No user called"):
        run("--make-admin", "nobody")
