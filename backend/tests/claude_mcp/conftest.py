import contextlib
import io
import secrets
import shutil
import tempfile
from datetime import timedelta

import httpx2
import pytest
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.utils import timezone
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from oauth2_provider.models import AccessToken, Application, set_token_value
from PIL import Image

from mcp_server.models import StagedImage

MCP_URL = "http://localhost:8400/mcp"



@pytest.fixture(autouse=True)
def _settings(settings, tmp_path):
    settings.MCP_PUBLIC_URL = "http://localhost:8400"
    settings.CMS_PUBLIC_URL = "https://cms.example.org"
    settings.MCP_OAUTH_AUTHORIZE_URL = "https://cms.example.org/oauth/authorize/"
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.ALLOWED_HOSTS = ["*"]
    from django.core.cache import cache

    cache.clear()


def make_user(username, role="editor", **extra):
    user = User.objects.create_user(username=username, password=secrets.token_urlsafe(12),
                                    first_name=extra.pop("first_name", username.title()), **extra)
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


@pytest.fixture
def editor(db):
    return make_user("priya", email="priya@example.org", last_name="Das")


@pytest.fixture
def claude_app(db):
    app = Application(name="Claude", client_type=Application.CLIENT_CONFIDENTIAL,
                      authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                      redirect_uris="https://claude.ai/api/mcp/auth_callback https://claude.com/api/mcp/auth_callback")
    app.client_secret = "test-secret-value"
    app.save()
    return app


def issue_token(user, application, scope="cms.drafts", expires_in=3600) -> str:
    raw = secrets.token_urlsafe(30)
    token = AccessToken(user=user, application=application, scope=scope,
                        expires=timezone.now() + timedelta(seconds=expires_in))
    set_token_value(token, raw)
    token.save()
    return raw


@pytest.fixture
def token(editor, claude_app):
    return issue_token(editor, claude_app)


@pytest.fixture
def asgi_app(settings):
    from mcp_server.app import build_app

    return build_app()


@contextlib.asynccontextmanager
async def running(app):
    async with app.router.lifespan_context(app):
        yield app


def http_client(app, token=None, **headers):
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost:8400",
                              headers=headers, timeout=20)


@contextlib.asynccontextmanager
async def mcp_client(app, token):
    async with running(app):
        async with http_client(app, token) as hc:
            async with Client(streamable_http_client(MCP_URL, http_client=hc), mode="legacy") as client:
                yield client


def png_bytes(width=1800, height=1000, fmt="PNG", color=(15, 76, 117)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, fmt)
    return buf.getvalue()


def stage_image(user, width=1800, height=1000) -> str:
    img = StagedImage(owner=user, sha256=secrets.token_hex(32), width=width, height=height, source="test")
    img.file.save("t.png", ContentFile(png_bytes(width, height)), save=False)
    img.save()
    return f"media:{img.pk}"
