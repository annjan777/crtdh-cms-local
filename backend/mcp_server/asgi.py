"""uvicorn mcp_server.asgi:app --host 0.0.0.0 --port 8400 --no-proxy-headers (behind the gateway/tunnel)."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from .app import build_app  # noqa: E402
from .proxy_guard import TrustedProxyGuard  # noqa: E402

# Outermost: refuses or strips untrusted peers before any route (Starlette or Django) runs.
app = TrustedProxyGuard(build_app())
