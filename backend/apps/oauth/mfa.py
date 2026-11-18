"""Adapter to backend-security's account state (apps/accounts on v3/backend-security).

- MFA: `apps.accounts.mfa.is_verified(request)` — active user whose session carries
  SESSION_FLAG == user.pk (set only by their password + TOTP login). Same rule as the
  fallback below, so the consent screen fails closed before their merge too.
- Temporary password: `UserSecurity.must_change_password`; such users finish the change at
  /cms/login before they may connect Claude.
"""

from django.conf import settings

try:
    from apps.accounts.mfa import SESSION_FLAG  # type: ignore
    from apps.accounts.mfa import is_verified as _is_verified  # type: ignore
except ImportError:  # TODO(integration, backend-security): always importable after their merge
    SESSION_FLAG = "crtdh_mfa_verified"
    _is_verified = None


def session_has_mfa(request) -> bool:
    if not getattr(settings, "MCP_OAUTH_REQUIRE_MFA", True):
        return True
    if _is_verified is not None:
        return bool(_is_verified(request))
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    return request.session.get(SESSION_FLAG) == user.pk


def must_change_password(user) -> bool:
    try:
        from apps.accounts.models import UserSecurity  # type: ignore
    except ImportError:  # TODO(integration, backend-security)
        return False
    return UserSecurity.objects.filter(user=user, must_change_password=True).exists()
