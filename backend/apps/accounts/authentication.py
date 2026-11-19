from rest_framework.authentication import SessionAuthentication

from apps.common.errors import CMSError

from .mfa import session_signed_in
from .models import UserSecurity


class CMSSessionAuthentication(SessionAuthentication):
    """Session cookie auth that enforces CSRF on every unsafe request, signed in
    or not (DRF's default skips CSRF for anonymous users, which would allow
    login CSRF). Returns 401 (not 403) when unauthenticated."""

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.enforce_csrf(request)
        if not user or not user.is_active:
            return None
        if not session_signed_in(request._request.session, user):
            return None  # no completed CMS sign-in (another Django login path, or password-only with MFA on)
        if self._must_change_password(user) and not getattr(request.parser_context.get("view"),
                                                             "allowed_before_password_change", False):
            raise CMSError("CMS_FORBIDDEN_ROLE", "Change your temporary password first.",
                           fix="Set a new password at POST /api/v1/auth/password/.")
        return (user, None)

    @staticmethod
    def _must_change_password(user):
        sec = UserSecurity.objects.filter(user=user).only("must_change_password").first()
        return bool(sec and sec.must_change_password)

    def authenticate_header(self, request):
        return "Session"
