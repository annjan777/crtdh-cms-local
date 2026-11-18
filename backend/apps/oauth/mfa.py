"""Adapter to backend-security's MFA state.

backend-security (v3/backend-security, apps/accounts/mfa.py) marks a session that passed
password + TOTP with `session[SESSION_FLAG] = user.pk` (mark_session_verified) and its
CMSSessionAuthentication accepts a session only when that flag equals the user's pk. The
consent screen applies the same rule, so it fails closed until a real MFA sign-in happens.
"""

from django.conf import settings

try:
    from apps.accounts.mfa import SESSION_FLAG  # type: ignore
except ImportError:  # TODO(integration, backend-security): import always succeeds after their merge
    SESSION_FLAG = "crtdh_mfa_verified"


def session_has_mfa(request) -> bool:
    if not getattr(settings, "MCP_OAUTH_REQUIRE_MFA", True):
        return True
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    return request.session.get(SESSION_FLAG) == user.pk
