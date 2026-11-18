"""
Django settings for the CRTDH CMS backend (config project).

See https://docs.djangoproject.com/en/5.0/topics/settings/
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
# Reads backend/.env if present; real deployments pass real env vars instead.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-me-in-production")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])


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
    "rest_framework_simplejwt",
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
    "django.middleware.security.SecurityMiddleware",
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


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# Default matches the docker-compose `db` service (postgres); override
# DATABASE_URL in .env for local dev (e.g. sqlite:///db.sqlite3).

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://crtdh:crtdh@db:5432/crtdh",
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static & media files
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "apps.publishing.permissions.ContentPermission",
    ),
    "EXCEPTION_HANDLER": "apps.publishing.errors.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}


# CORS
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:3001"],
)


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
# Optional: lets an internal caller (same host) set X-CMS-Channel via X-CMS-Internal. Empty = header ignored.
CMS_INTERNAL_SECRET = env("CMS_INTERNAL_SECRET", default="")
UPLOAD_LINK_TTL_MINUTES = env.int("UPLOAD_LINK_TTL_MINUTES", default=30)
DJANGO_ADMIN_READONLY = env.bool("DJANGO_ADMIN_READONLY", default=not DEBUG)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="CRTDH CMS <cms@localhost>")
CMS_PUBLIC_URL = env("CMS_PUBLIC_URL", default="http://localhost:3200")
