import json

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.roles import user_roles


def test_refuses_without_flag(db, monkeypatch):
    monkeypatch.delenv("CRTDH_ALLOW_TEST_SEED", raising=False)
    with pytest.raises(CommandError, match="CRTDH_ALLOW_TEST_SEED"):
        call_command("seed_test_users")


def test_refuses_in_production_without_rehearsal(db, monkeypatch):
    monkeypatch.setenv("CRTDH_ALLOW_TEST_SEED", "1")
    monkeypatch.setenv("CRTDH_TEST_PASSWORD", "x" * 16)
    monkeypatch.setenv("DJANGO_ENV", "production")
    with pytest.raises(CommandError, match="production"):
        call_command("seed_test_users")


def test_creates_one_user_per_role(db, monkeypatch, capsys):
    monkeypatch.setenv("CRTDH_ALLOW_TEST_SEED", "1")
    monkeypatch.setenv("CRTDH_TEST_PASSWORD", "x" * 16)
    monkeypatch.setenv("DJANGO_ENV", "test")
    call_command("seed_test_users", "--no-mfa")
    out = json.loads(capsys.readouterr().out)
    from django.contrib.auth import get_user_model
    U = get_user_model()
    assert user_roles(U.objects.get(username="erin_editor")) == ["editor"]
    assert user_roles(U.objects.get(username="priya")) == ["editor", "publisher"]
    assert user_roles(U.objects.get(username="ada_admin"))[-1] == "admin"
    assert "x" * 16 not in json.dumps(out)
