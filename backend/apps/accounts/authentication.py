from rest_framework.authentication import SessionAuthentication

from .mfa import SESSION_FLAG


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
        if request._request.session.get(SESSION_FLAG) != user.pk:
            return None  # signed in without MFA (e.g. some other Django login path): not a CMS session
        return (user, None)

    def authenticate_header(self, request):
        return "Session"
