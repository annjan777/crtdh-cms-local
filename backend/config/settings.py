"""
Django settings for the CRTDH CMS backend.

Everything comes from the environment (see backend/.env.example). Production
(DEBUG false, or CRTDH_ENV=production) fails closed: config/security.py lists
the checks, and the process refuses to start if any fails.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from config.security import production_problems

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# backend/.env is a developer convenience; deployments pass real env vars.
# Tests set CRTDH_SKIP_DOTENV=1 so a developer's .env never leaks into them.
if env("CRTDH_SKIP_DOTENV", default="0") != "1":
    environ.Env.read_env(BASE_DIR / ".env")

CRTDH_ENV = env("CRTDH_ENV", default="development")
DEBUG = env.bool("DEBUG", default=False)
IS_PRODUCTION = not DEBUG or CRTDH_ENV == "production"

SECRET_KEY = env("SECRET_KEY", default="")
if DEBUG and not SECRET_KEY and CRTDH_ENV != "production":
    SECRET_KEY = get_random_secret_key()  # dev only: new key per process

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"] if DEBUG else [])

# The Django admin bypasses the MFA login, so it exists only in local dev.
DJANGO_ADMIN_ENABLED = env.bool("DJANGO_ADMIN_ENABLED", default=False)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    # local apps
    "apps.common",
    "apps.core",
    "apps.carousel",
    "apps.team",
    "apps.facilities",
    "apps.services",
    "apps.innovations",
    "apps.products",
    "apps.enterprises",
    "apps.media_gallery",
    "apps.contact",
    "apps.accounts",
]

MIDDLEWARE = [
    "apps.common.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database: required in production (no default credentials).
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///" + str(BASE_DIR / "db.sqlite3") if DEBUG else "")}
if not DATABASES["default"].get("ENGINE"):
    raise ImproperlyConfigured("DATABASE_URL is required when DEBUG is false.")
DATABASES["default"].setdefault("CONN_MAX_AGE", env.int("DB_CONN_MAX_AGE", default=60))
ALLOW_SQLITE = env.bool("ALLOW_SQLITE", default=False)

# Shared cache (throttling, lockout counters) must be shared by every worker:
# the database cache needs `manage.py createcachetable` once.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "crtdh_cache",
    }
}


# Passwords and auth

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Lockout with exponential backoff (apps/accounts/lockout.py).
AUTH_LOCKOUT = {
    "USER_THRESHOLD": env.int("AUTH_LOCKOUT_USER_THRESHOLD", default=5),
    "IP_THRESHOLD": env.int("AUTH_LOCKOUT_IP_THRESHOLD", default=20),
    "BASE_SECONDS": 60,
    "MAX_SECONDS": 3600,
    "RESET_AFTER_SECONDS": 24 * 3600,
}
MFA_ISSUER = env("MFA_ISSUER", default="CRTDH CMS")
MFA_PENDING_SECONDS = 300  # time allowed between the password step and the TOTP step

# Sessions: HttpOnly, SameSite=Strict, Secure in production, 8 h absolute lifetime.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_NAME = "__Host-crtdh_session" if IS_PRODUCTION else "crtdh_session"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=8 * 3600)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF: the token is handed to the SPA by GET /api/v1/auth/csrf/ (body + cookie),
# so the cookie itself stays HttpOnly.
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_NAME = "__Host-crtdh_csrf" if IS_PRODUCTION else "crtdh_csrf"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_FAILURE_VIEW = "apps.common.errors.csrf_failure"


# Transport and headers

# Behind the Cloudflare tunnel, TLS ends at Cloudflare; cloudflared forwards
# X-Forwarded-Proto. gunicorn is never published on a host port, so the header
# cannot be forged by a client reaching it directly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=IS_PRODUCTION)
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# The CMS API returns JSON only; nothing it serves may run script or be framed.
CONTENT_SECURITY_POLICY = env(
    "CONTENT_SECURITY_POLICY",
    default="default-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), "
    "microphone=(), payment=(), usb=(), interest-cohort=()"
)

# Client IP: trust Cloudflare's CF-Connecting-IP only when the app is reachable
# solely through the tunnel (deploy/docker-compose.yml). Never in dev.
TRUST_CF_CONNECTING_IP = env.bool("TRUST_CF_CONNECTING_IP", default=False)


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static & media. MEDIA_ROOT is private storage, never a web root: the CMS
# reads files through the authenticated /api/v1/media/ view and the publish
# build copies them into the static site.

STATIC_URL = "static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
MEDIA_URL = "/api/v1/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
UPLOAD_LIMITS = {
    "image": env.int("UPLOAD_MAX_IMAGE_BYTES", default=15 * 1024 * 1024),
    "document": env.int("UPLOAD_MAX_DOCUMENT_BYTES", default=20 * 1024 * 1024),
    "video": env.int("UPLOAD_MAX_VIDEO_BYTES", default=200 * 1024 * 1024),
}
IMAGE_MAX_PIXELS = 60_000_000  # decompression-bomb ceiling (e.g. 9000 x 6600)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.accounts.authentication.CMSSessionAuthentication",),
    # Fail closed: a view that forgets permission_classes needs an editor.
    "DEFAULT_PERMISSION_CLASSES": ("apps.accounts.roles.IsEditor",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "contact": env("CONTACT_THROTTLE_RATE", default="5/min"),
        "auth": env("AUTH_THROTTLE_RATE", default="20/min"),
    },
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += ("rest_framework.renderers.BrowsableAPIRenderer",)


# CORS: only the public contact endpoint is cross-origin (the static site posts
# to contact.<domain>); the admin SPA is same-origin with the API.

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_URLS_REGEX = env("CORS_URLS_REGEX", default=r"^/api/v1/contact/$")
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)


# Contact relay

TURNSTILE_SECRET = env("TURNSTILE_SECRET", default="")
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", default="")
CONTACT_RETENTION_DAYS = env.int("CONTACT_RETENTION_DAYS", default=365)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="CRTDH website <no-reply@localhost>")
_email = env.email_url("EMAIL_URL", default="consolemail://" if DEBUG else "dummymail://")
EMAIL_BACKEND = _email["EMAIL_BACKEND"]
for _k in ("EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "EMAIL_USE_TLS", "EMAIL_USE_SSL"):
    if _k in _email:
        globals()[_k] = _email[_k]
EMAIL_TIMEOUT = 10


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "crtdh.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


# Fail closed in production.
_problems = production_problems(
    debug=DEBUG,
    env_name=CRTDH_ENV,
    secret_key=SECRET_KEY,
    allowed_hosts=ALLOWED_HOSTS,
    cors_allow_all=CORS_ALLOW_ALL_ORIGINS,
    cors_origins=CORS_ALLOWED_ORIGINS,
    csrf_trusted_origins=CSRF_TRUSTED_ORIGINS,
    database_engine=DATABASES["default"]["ENGINE"],
    allow_sqlite=ALLOW_SQLITE,
    django_admin_enabled=DJANGO_ADMIN_ENABLED,
)
if _problems:
    raise ImproperlyConfigured("Refusing to start with unsafe production settings: " + "; ".join(_problems))
