"""Test settings (QA lane). Used by pytest via backend/pytest.ini.

Imports the real settings so tests exercise production code paths, then swaps in
SQLite, fast hashing, in-memory email/cache and a throwaway MEDIA_ROOT.
Env vars are set *before* the import so fail-closed production checks see sane values.
"""
import os
import tempfile

os.environ.setdefault("SECRET_KEY", "test-only-not-a-secret-0123456789abcdefghijklmnopqrstuvwxyz")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
os.environ.setdefault("CORS_ALLOW_ALL_ORIGINS", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CRTDH_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE", "1")
os.environ.setdefault("SECURE_SSL_REDIRECT", "False")
os.environ.setdefault("CRTDH_SKIP_DOTENV", "1")  # keep a dev backend/.env out of tests

from .settings import *  # noqa: E402,F401,F403

MFA_ENABLED = True  # the suite covers the MFA flow; tests for MFA off override this

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
if os.environ.get("TEST_DATABASE_URL"):  # CI runs the suite on Postgres 16 too (production engine)
    import environ

    DATABASES = {"default": environ.Env.db_url_config(os.environ["TEST_DATABASE_URL"])}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
MEDIA_ROOT = tempfile.mkdtemp(prefix="crtdh-test-media-")
# Turnstile / external calls must never leave the box in tests.
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "1x0000000000000000000000000000000AA")  # Cloudflare always-pass test key; tests mock verify anyway
