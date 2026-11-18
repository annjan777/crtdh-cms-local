"""uvicorn mcp_server.asgi:app --host 127.0.0.1 --port 8400 (behind the Cloudflare tunnel)."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from .app import build_app  # noqa: E402

app = build_app()
