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
    monkeypatch.setenv("CRTDH_ENV", "production")
    with pytest.raises(CommandError, match="production"):
        call_command("seed_test_users")


def test_creates_one_user_per_role(db, monkeypatch, capsys):
    monkeypatch.setenv("CRTDH_ALLOW_TEST_SEED", "1")
    monkeypatch.setenv("CRTDH_TEST_PASSWORD", "x" * 16)
    monkeypatch.setenv("CRTDH_ENV", "test")
    call_command("seed_test_users", "--no-mfa")
    out = json.loads(capsys.readouterr().out)
    from django.contrib.auth import get_user_model
    U = get_user_model()
    assert user_roles(U.objects.get(username="erin_editor")) == ["editor"]
    assert user_roles(U.objects.get(username="priya")) == ["editor", "publisher"]
    assert user_roles(U.objects.get(username="ada_admin"))[-1] == "admin"
    assert "x" * 16 not in json.dumps(out)


def test_production_config_never_allows_test_seeding():
    """R-9 / F-09: test users must not be creatable on production. The production compose file and the env
    template must not set CRTDH_ALLOW_TEST_SEED, and production runs with CRTDH_ENV=production."""
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[3]
    compose = yaml.safe_load((root / "deploy/docker-compose.yml").read_text())
    for name, svc in compose["services"].items():
        env = svc.get("environment") or {}
        env = env if isinstance(env, dict) else dict(e.split("=", 1) for e in env if "=" in e)
        assert "CRTDH_ALLOW_TEST_SEED" not in env, name
    assert compose["services"]["cms"]["environment"]["CRTDH_ENV"] == "production"
    example = (root / "deploy/.env.example").read_text().splitlines()
    assert not [ln for ln in example if ln.strip().startswith("CRTDH_ALLOW_TEST_SEED")]
