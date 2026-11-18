"""Bearer-token check for /mcp against django-oauth-toolkit's token table.

Runs on every HTTP request, so a revoked token, a deactivated user or an expired token is
refused on Claude's very next call, including inside an already-open MCP session.
"""

from __future__ import annotations

import hashlib

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone
from mcp.server.auth.provider import AccessToken as SdkAccessToken
from mcp.server.auth.provider import TokenVerifier
from oauth2_provider.models import get_access_token_model


def lookup_token(raw: str) -> SdkAccessToken | None:
    if not raw or len(raw) > 512:
        return None
    checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    token = (
        get_access_token_model()
        .objects.select_related("user", "application")
        .filter(token_checksum=checksum)
        .first()
    )
    if token is None or token.user is None or token.application is None:
        return None
    if token.expires <= timezone.now() or not token.user.is_active:
        return None
    scopes = token.scope.split()
    if settings.MCP_OAUTH_SCOPE not in scopes:
        return None
    return SdkAccessToken(
        token="",  # never keep the raw token in memory longer than needed
        client_id=token.application.client_id,
        scopes=scopes,
        expires_at=int(token.expires.timestamp()),
        subject=str(token.user_id),
        claims={"token_pk": token.pk},
    )


class DjangoTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> SdkAccessToken | None:
        return await sync_to_async(lookup_token, thread_sensitive=True)(token)
