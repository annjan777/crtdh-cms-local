"""WS0 regressions: no default admin, no reseed in prod, fail-closed production config."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.security]
BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
PROD_SETTINGS = os.environ.get("PROD_SETTINGS_MODULE", "config.settings")


@pytest.mark.needs_integration
def test_seed_fixture_has_no_users():
    data = json.loads((BACKEND / "apps/core/fixtures/local_seed.json").read_text())
    assert not [o for o in data if o["model"].startswith("auth.")]


@pytest.mark.needs_integration
def test_prod_compose_does_not_reseed():
    assert "bootstrap_local" not in (REPO / "deploy/docker-compose.yml").read_text()


@pytest.mark.needs_integration
def test_deploy_env_not_tracked():
    out = subprocess.run(["git", "ls-files", "deploy/.env"], cwd=REPO, capture_output=True, text=True).stdout
    assert out.strip() == ""


def _start(env_over):
    env = {k: v for k, v in os.environ.items() if k not in ("DEBUG", "SECRET_KEY", "ALLOWED_HOSTS", "CORS_ALLOW_ALL_ORIGINS")}
    env.update({"DJANGO_SETTINGS_MODULE": PROD_SETTINGS, "CRTDH_ENV": "production",
                "SECRET_KEY": __import__("secrets").token_urlsafe(64), "ALLOWED_HOSTS": "cms.example.test", "CORS_ALLOW_ALL_ORIGINS": "False",
                "DATABASE_URL": "sqlite:////tmp/never-used.sqlite3", "ALLOW_SQLITE": "1"})
    env.update(env_over)
    return subprocess.run([sys.executable, "-c", "import django; django.setup(); from django.conf import settings; settings.SECRET_KEY"],
                          cwd=BACKEND, env=env, capture_output=True, text=True)


@pytest.mark.needs_integration
def test_prod_settings_start_when_sane():
    r = _start({})
    assert r.returncode == 0, r.stderr[-800:]


@pytest.mark.needs_integration
@pytest.mark.parametrize("bad", [
    {"DEBUG": "True"},
    {"SECRET_KEY": "django-insecure-dev-key-change-me-in-production"},
    {"SECRET_KEY": ""},
    {"ALLOWED_HOSTS": "*"},
    {"CORS_ALLOW_ALL_ORIGINS": "True"},
])
def test_prod_settings_fail_closed(bad):
    r = _start(bad)
    assert r.returncode != 0, f"production settings started with {bad}"


@pytest.mark.needs_integration
def test_no_hardcoded_default_admin_password_in_repo():
    """Found 19 Nov: docker-compose.local.yml sets DJANGO_SUPERUSER_PASSWORD "adminpassword"."""
    out = subprocess.run(["git", "grep", "-n", "-I", "adminpassword", "--", ".", ":!backend/tests", ":!docs"],
                         cwd=REPO, capture_output=True, text=True).stdout
    assert out.strip() == "", out
