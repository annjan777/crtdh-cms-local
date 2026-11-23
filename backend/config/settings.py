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
    "apps.publishing",
]

MIDDLEWARE = [
    "apps.common.middleware.TrustedProxyMiddleware",
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
# Two-step sign-in (TOTP). Off: password alone signs in, and every MFA screen, endpoint and admin
# control is hidden (the endpoints answer 404). The code, data and tests stay, so it can be turned back on
# by setting MFA_ENABLED=True; anyone already enrolled is asked for their code again from then on.
MFA_ENABLED = env.bool("MFA_ENABLED", default=False)
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

# Behind the Cloudflare tunnel, TLS ends at Cloudflare; the gateway/cloudflared send
# X-Forwarded-Proto. Not publishing a host port does NOT stop a process on the server
# from reaching the container directly, so TrustedProxyMiddleware strips forwarding
# headers from any peer outside TRUSTED_PROXY_IPS (and refuses it with REQUIRE_TRUSTED_PROXY).
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

# Proxies: the TCP peers allowed to set forwarding headers (gateway nginx and cloudflared at fixed
# addresses on the compose network, deploy/docker-compose.yml). IPs or CIDRs.
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=[])
# Refuse every request whose peer is not a trusted proxy (production compose sets this).
REQUIRE_TRUSTED_PROXY = env.bool("REQUIRE_TRUSTED_PROXY", default=False)
# Client IP: use Cloudflare's CF-Connecting-IP (lockout, throttles, logs) only when this is on and
# the request came from a trusted proxy; otherwise the peer address. Never in dev.
TRUST_CF_CONNECTING_IP = env.bool("TRUST_CF_CONNECTING_IP", default=False)
# Behind a plain Apache reverse proxy on the same host (deploy/academicweb): mod_proxy appends the client to
# X-Forwarded-For and sends X-Forwarded-Host, but no X-Forwarded-Proto. Only for peers in TRUSTED_PROXY_IPS:
# the client IP is the LAST X-Forwarded-For entry (the one the proxy added, never one the client sent), the host
# comes from X-Forwarded-Host, and a missing X-Forwarded-Proto counts as FORWARDED_PROTO_DEFAULT.
TRUST_X_FORWARDED_FOR = env.bool("TRUST_X_FORWARDED_FOR", default=False)
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)
FORWARDED_PROTO_DEFAULT = env("FORWARDED_PROTO_DEFAULT", default="")
# The admin SPA's build folder, served under /cms/ when there is no gateway of our own (apps.common.admin_app).
ADMIN_DIST_DIR = env("ADMIN_DIST_DIR", default="")


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
# Where the CMS's own screens find photos. A host that reaches the CMS under a sub-path (deploy/academicweb:
# /cms/index.php/) sets this to that path + /api/v1/media/; stored content keeps file names, never these URLs.
MEDIA_URL = env("MEDIA_URL", default="/api/v1/media/")
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
    # Fail closed: a view that forgets permission_classes needs an editor; DELETE needs a publisher (contract §3).
    "DEFAULT_PERMISSION_CLASSES": ("apps.publishing.permissions.ContentPermission",),
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
if EMAIL_BACKEND.endswith("filebased.EmailBackend"):
    # filemail:///abs/dir (rehearsal/dev). Read the path from the URL itself: django-environ drops its leading "/".
    _path = env("EMAIL_URL").split("://", 1)[1].split("?", 1)[0]
    EMAIL_FILE_PATH = "/" + _path.lstrip("/") if _path.startswith("/") else str(Path(_path).resolve())
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
    trust_cf_connecting_ip=TRUST_CF_CONNECTING_IP,
    trusted_proxy_ips=TRUSTED_PROXY_IPS,
    require_trusted_proxy=REQUIRE_TRUSTED_PROXY,
)
if _problems:
    raise ImproperlyConfigured("Refusing to start with unsafe production settings: " + "; ".join(_problems))


# ---------------------------------------------------------------------------
# Publishing (backend-core lane; contract §1, §3, §5)
# ---------------------------------------------------------------------------
# Where snapshots, build dirs, content-hashed media and tarballs live (never inside MEDIA_ROOT).
PUBLISH_ROOT = env("PUBLISH_ROOT", default=str(BASE_DIR / "var" / "publish"))
# Frontend build: run with SNAPSHOT_PATH and BUILD_OUTPUT_DIR in the environment, cwd = BASE_DIR.
FRONTEND_BUILD_CMD = env("FRONTEND_BUILD_CMD", default="npm --prefix ../frontend run build")
FRONTEND_BUILD_OUTPUT = env("FRONTEND_BUILD_OUTPUT", default=str(BASE_DIR.parent / "frontend" / "build" / "client"))
FRONTEND_BUILD_TIMEOUT = env.int("FRONTEND_BUILD_TIMEOUT", default=900)
# Shared secret with the publish agent (HMAC-SHA256, contract agreed with publish-agent). Empty = agent endpoints refuse every request.
AGENT_HMAC_SECRET = env("AGENT_HMAC_SECRET", default="")
AGENT_MAX_SKEW = env.int("AGENT_MAX_SKEW", default=300)
# An "uploading" publish with no status report from the agent for this many seconds is marked failed, so a dead
# or stuck agent can't wedge publishing (single-flight) until someone edits the database.
PUBLISH_STALE_UPLOAD_AFTER = env.int("PUBLISH_STALE_UPLOAD_AFTER", default=1800)
# Optional: lets an internal caller (same host) set X-CMS-Channel via X-CMS-Internal. Empty = header ignored.
CMS_INTERNAL_SECRET = env("CMS_INTERNAL_SECRET", default="")
UPLOAD_LINK_TTL_MINUTES = env.int("UPLOAD_LINK_TTL_MINUTES", default=30)
DJANGO_ADMIN_READONLY = env.bool("DJANGO_ADMIN_READONLY", default=not DEBUG)
CMS_PUBLIC_URL = env("CMS_PUBLIC_URL", default="http://localhost:3200")


# Claude MCP server + OAuth authorization server (WS4) — see config/mcp_settings.py
from .mcp_settings import *  # noqa: E402,F401,F403
from .mcp_settings import MCP_ALLOWED_HOSTS, MCP_INSTALLED_APPS  # noqa: E402

INSTALLED_APPS += MCP_INSTALLED_APPS
ALLOWED_HOSTS = [*ALLOWED_HOSTS, *(h for h in MCP_ALLOWED_HOSTS if h not in ALLOWED_HOSTS)]
