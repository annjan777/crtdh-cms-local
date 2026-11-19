"""Account state the OAuth consent step needs, from apps.accounts.

- MFA: `apps.accounts.mfa.is_verified(request)`: an active user whose session is a completed CMS sign-in (with a
  code when MFA_ENABLED). MCP_OAUTH_REQUIRE_MFA=False skips the check (tests and local tools only).
- Temporary password: `UserSecurity.must_change_password`; such users finish the change at /cms/login before
  they may connect Claude.
"""

from django.conf import settings

from apps.accounts.mfa import SESSION_FLAG, is_verified

__all__ = ["SESSION_FLAG", "session_has_mfa", "must_change_password"]


def session_has_mfa(request) -> bool:
    if not getattr(settings, "MCP_OAUTH_REQUIRE_MFA", True):
        return True
    return bool(is_verified(request))


def must_change_password(user) -> bool:
    from apps.accounts.models import UserSecurity

    return UserSecurity.objects.filter(user=user, must_change_password=True).exists()
