"""Fail-closed production settings (TEST-PLAN: production settings refuse to start)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config.security import production_problems, secret_key_problem

pytestmark = pytest.mark.security
BACKEND = Path(__file__).resolve().parents[2]
GOOD_KEY = "q" + "Zx8-vT1_mK4pR7sW0yB3nE6hJ9cF2gL5" * 2
PROD = {
    "DEBUG": "False", "SECRET_KEY": GOOD_KEY, "ALLOWED_HOSTS": "cms.example.org",
    "DATABASE_URL": "postgres://u:p@db:5432/crtdh", "CORS_ALLOWED_ORIGINS": "https://crtdh.example.org",
    "CSRF_TRUSTED_ORIGINS": "https://cms.example.org", "CRTDH_SKIP_DOTENV": "1", "CRTDH_ENV": "production",
}


def load(**overrides):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "DEBUG", "SECRET", "ALLOWED", "CORS",
                                                                     "DATABASE", "CSRF", "ALLOW_", "CRTDH", "SECURE"))}
    env.update(PROD)
    env.update({k: v for k, v in overrides.items() if v is not None})
    for k, v in overrides.items():
        if v is None:
            env.pop(k, None)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    code = ("import django, json; from django.conf import settings; django.setup();"
            "print(json.dumps({k: str(getattr(settings, k)) for k in "
            "['SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE','SECURE_HSTS_SECONDS','SECURE_SSL_REDIRECT',"
            "'SESSION_COOKIE_SAMESITE','X_FRAME_OPTIONS','SESSION_COOKIE_NAME']}))")
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)


def test_good_production_config_starts_with_secure_defaults():
    r = load()
    assert r.returncode == 0, r.stderr
    s = json.loads(r.stdout.strip().splitlines()[-1])
    assert s["SESSION_COOKIE_SECURE"] == "True" and s["CSRF_COOKIE_SECURE"] == "True"
    assert s["SECURE_HSTS_SECONDS"] == "31536000" and s["SECURE_SSL_REDIRECT"] == "True"
    assert s["SESSION_COOKIE_SAMESITE"] == "Strict" and s["X_FRAME_OPTIONS"] == "DENY"
    assert s["SESSION_COOKIE_NAME"].startswith("__Host-")


@pytest.mark.parametrize("overrides,needle", [
    ({"SECRET_KEY": None}, "SECRET_KEY is not set"),
    ({"SECRET_KEY": "django-insecure-dev-key-change-me-in-production"}, "known default"),
    ({"SECRET_KEY": "local-secret-key-123"}, "known default"),
    ({"SECRET_KEY": "short-but-random-Xy7"}, "too short"),
    ({"ALLOWED_HOSTS": "*"}, "wildcard"),
    ({"ALLOWED_HOSTS": "cms.example.org,*"}, "wildcard"),
    ({"ALLOWED_HOSTS": None}, "ALLOWED_HOSTS is empty"),
    ({"CORS_ALLOW_ALL_ORIGINS": "True"}, "CORS_ALLOW_ALL_ORIGINS"),
    ({"CORS_ALLOWED_ORIGINS": "http://crtdh.example.org"}, "not https"),
    ({"CSRF_TRUSTED_ORIGINS": "https://*.example.org"}, "wildcard origin"),
    ({"DEBUG": "True"}, "DEBUG is true while CRTDH_ENV=production"),
    ({"DATABASE_URL": "sqlite:///db.sqlite3"}, "sqlite"),
    ({"DATABASE_URL": None}, "DATABASE_URL is required"),
    ({"DJANGO_ADMIN_ENABLED": "True"}, "DJANGO_ADMIN_ENABLED"),
])
def test_unsafe_production_config_refuses_to_start(overrides, needle):
    r = load(**overrides)
    assert r.returncode != 0
    assert needle in r.stderr, r.stderr[-800:]
    assert GOOD_KEY not in r.stderr


def test_sqlite_allowed_only_with_explicit_flag():
    assert load(DATABASE_URL="sqlite:///x.db", ALLOW_SQLITE="1").returncode == 0


def test_debug_without_production_marker_is_dev():
    assert load(DEBUG="True", CRTDH_ENV="development", SECRET_KEY=None, DATABASE_URL=None,
                ALLOWED_HOSTS=None, CORS_ALLOWED_ORIGINS=None, CSRF_TRUSTED_ORIGINS=None).returncode == 0


def test_secret_key_rules():
    assert secret_key_problem(GOOD_KEY) is None
    assert secret_key_problem("a" * 60)  # too simple
    assert production_problems(debug=False, env_name="production", secret_key=GOOD_KEY, allowed_hosts=["x"],
                               cors_allow_all=False, cors_origins=[], csrf_trusted_origins=[],
                               database_engine="django.db.backends.postgresql", allow_sqlite=False,
                               django_admin_enabled=False) == []
