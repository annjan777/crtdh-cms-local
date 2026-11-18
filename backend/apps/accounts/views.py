"""CMS authentication (contract §3 Auth).

Sign-in is two steps: POST /auth/login/ checks the password and parks the user
in a short "pending" state in the session; POST /auth/mfa/ (or the enrol
confirm step, for a first sign-in) checks the TOTP code and only then creates
the authenticated session. A session therefore always means password + MFA.
"""
import logging
import time

from django.contrib.auth import authenticate, get_user_model, login, logout, password_validation
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.errors import CMSError
from apps.common.middleware import client_ip
from apps.common.throttles import IPScopedThrottle

from . import lockout, mfa, sessions
from .models import UserSecurity
from .roles import user_roles

logger = logging.getLogger("crtdh.security")
User = get_user_model()
PENDING = "crtdh_pre_auth"
BACKEND = "django.contrib.auth.backends.ModelBackend"


def me_payload(user):
    sec = getattr(user, "security", None)
    return {
        "id": user.id,
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "email": user.email,
        "roles": user_roles(user),
        "mfa_enrolled": mfa.is_enrolled(user),
        "must_change_password": bool(sec and sec.must_change_password),
    }


def _str(request, key, max_len):
    val = request.data.get(key, "")
    if not isinstance(val, str) or not val or len(val) > max_len:
        raise CMSError("CMS_VALIDATION", f"`{key}` is required.", fix=f"Send `{key}` as text.", field=key)
    return val


def _check_lock(request, username):
    wait = lockout.retry_after(lockout.keys_for(username, client_ip(request)))
    if wait:
        raise CMSError(
            "CMS_RATE_LIMITED", f"Too many failed attempts. Try again in {wait} seconds.",
            fix="Wait, then sign in again. An admin can reset your MFA if you lost your device.",
            retryable=True, headers={"Retry-After": str(wait)},
        )


def _fail(request, username, message):
    lockout.register_failure(lockout.keys_for(username, client_ip(request)))
    logger.warning("auth failure user=%r ip=%s", username[:150], client_ip(request))
    raise CMSError("CMS_UNAUTHENTICATED", message, fix="Check and try again.")


def _pending_user(request):
    data = request.session.get(PENDING)
    if not data or time.time() - data.get("at", 0) > settings.MFA_PENDING_SECONDS:
        raise CMSError("CMS_UNAUTHENTICATED", "Your sign-in step expired.", fix="Enter your password again.")
    user = User.objects.filter(pk=data["uid"], is_active=True).first()
    if not user or user.get_session_auth_hash() != data.get("hash"):
        request.session.pop(PENDING, None)
        raise CMSError("CMS_UNAUTHENTICATED", "Your sign-in step expired.", fix="Enter your password again.")
    return user


def _complete_login(request, user):
    request.session.pop(PENDING, None)
    login(request, user, backend=BACKEND)  # cycles the session key and rotates the CSRF token
    mfa.mark_session_verified(request.session, user)
    sessions.track(request, user)
    lockout.clear(user.get_username())
    logger.info("auth success user=%s ip=%s", user.get_username(), client_ip(request))
    return dict(me_payload(user), csrfToken=get_token(request))


class _AuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [IPScopedThrottle]
    throttle_scope = "auth"


class CsrfView(_AuthView):
    """GET /api/v1/auth/csrf/ - sets the CSRF cookie and returns the token for X-CSRFToken."""

    throttle_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(_AuthView):
    def post(self, request):
        username = _str(request, "username", 150)
        password = _str(request, "password", 1024)
        _check_lock(request, username)
        user = authenticate(request, username=username, password=password)
        if user is None:
            _fail(request, username, "Wrong username or password.")
        request.session.cycle_key()
        request.session[PENDING] = {"uid": user.pk, "at": time.time(), "hash": user.get_session_auth_hash()}
        return Response({"mfa_required": True, "mfa_enrolled": mfa.is_enrolled(user)})


class MFAView(_AuthView):
    """POST /api/v1/auth/mfa/ {code} - TOTP or recovery code; completes sign-in."""

    def post(self, request):
        user = _pending_user(request)
        code = _str(request, "code", 64)
        _check_lock(request, user.get_username())
        if not mfa.is_enrolled(user):
            raise CMSError("CMS_MFA_REQUIRED", "Set up your authenticator app first.",
                           fix="Call POST /api/v1/auth/mfa/enrol/.")
        if not mfa.verify_code(user, code):
            _fail(request, user.get_username(), "Wrong or already-used code.")
        return Response(_complete_login(request, user))


class MFAEnrolView(_AuthView):
    """POST /api/v1/auth/mfa/enrol/ - first sign-in only (after the password step)."""

    def post(self, request):
        user = _pending_user(request)
        if mfa.is_enrolled(user):
            raise CMSError("CMS_FORBIDDEN_ROLE", "MFA is already set up for this account.",
                           fix="Sign in with your code. An admin can reset MFA if you lost the device.")
        return Response(mfa.start_enrolment(user))


class MFAEnrolConfirmView(_AuthView):
    """POST /api/v1/auth/mfa/enrol/confirm/ {code} - confirms, returns recovery codes once, signs in."""

    def post(self, request):
        user = _pending_user(request)
        code = _str(request, "code", 16)
        _check_lock(request, user.get_username())
        codes = mfa.confirm_enrolment(user, code)
        if codes is None:
            _fail(request, user.get_username(), "That code did not match. Check the time on your phone.")
        return Response(dict(_complete_login(request, user), recovery_codes=codes))


class RecoveryCodesView(APIView):
    """POST /api/v1/auth/mfa/recovery-codes/ {code} - new set of recovery codes (old ones die)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [IPScopedThrottle]
    throttle_scope = "auth"

    def post(self, request):
        _check_lock(request, request.user.get_username())
        if not mfa.verify_code(request.user, _str(request, "code", 64)):
            _fail(request, request.user.get_username(), "Wrong or already-used code.")
        return Response({"recovery_codes": mfa.regenerate_recovery_codes(request.user)})


class LogoutView(APIView):
    allowed_before_password_change = True
    permission_classes = [AllowAny]

    def post(self, request):
        key = request.session.session_key
        if request.user.is_authenticated and key:
            request.user.cms_sessions.filter(session_key=key).delete()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    allowed_before_password_change = True
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(me_payload(request.user))


class RevokeAllSessionsView(APIView):
    allowed_before_password_change = True
    """POST /api/v1/auth/sessions/revoke-all/ - signs this user out everywhere, including here."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        n = sessions.revoke_all(user)
        logout(request)
        return Response({"revoked": n})


class PasswordChangeView(APIView):
    allowed_before_password_change = True
    """POST /api/v1/auth/password/ {current_password, new_password} - keeps this session, ends the others."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [IPScopedThrottle]
    throttle_scope = "auth"

    def post(self, request):
        user = request.user
        current = _str(request, "current_password", 1024)
        new = _str(request, "new_password", 1024)
        _check_lock(request, user.get_username())
        if not user.check_password(current):
            _fail(request, user.get_username(), "Current password is wrong.")
        try:
            password_validation.validate_password(new, user)
        except DjangoValidationError as e:
            raise CMSError("CMS_VALIDATION", " ".join(e.messages), fix="Choose a longer, less common password.",
                           field="new_password")
        user.set_password(new)
        user.save(update_fields=["password"])
        update_session_auth_hash(request, user)  # cycles this session's key
        sessions.track(request, user)
        sessions.revoke_all(user, keep=request.session.session_key)
        UserSecurity.objects.filter(user=user).update(must_change_password=False)
        return Response(dict(me_payload(user), csrfToken=get_token(request)))
