"""Adapter to backend-security's MFA state.

TODO(integration, backend-security): replace the fallback with the real check once
`apps.accounts` exposes it (asked in inbox/backend-security.md). Until then a session counts
as MFA-verified only if it carries SESSION_KEY, which nothing but backend-security's TOTP
step (or a test) sets, so the consent screen fails closed.
"""

from django.conf import settings

SESSION_KEY = "mfa_verified"


def session_has_mfa(request) -> bool:
    if not getattr(settings, "MCP_OAUTH_REQUIRE_MFA", True):
        return True
    try:  # pragma: no cover - exercised after backend-security merges
        from apps.accounts.mfa import is_verified  # type: ignore

        return bool(is_verified(request))
    except ImportError:
        return bool(request.session.get(SESSION_KEY))
