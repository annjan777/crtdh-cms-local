"""TOTP MFA and recovery codes. `verify_code(user, code)` is the one check used
by the CMS login."""
import base64
import hashlib
import hmac
import io
import secrets
import time

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import RecoveryCode, UserSecurity

RECOVERY_CODE_COUNT = 10
SESSION_FLAG = "crtdh_mfa_verified"  # set when sign-in completes; checked on every request
# How the session signed in: "totp" (password + code) or "password" (MFA_ENABLED off). With MFA on, only "totp"
# sessions count, so switching MFA on ends every password-only session at once (they sign in again with a code).
SESSION_METHOD = "crtdh_auth_method"
STEP = 30


def security_for(user):
    sec, _ = UserSecurity.objects.get_or_create(user=user)
    return sec


def is_enrolled(user):
    sec = UserSecurity.objects.filter(user=user).first()
    return bool(sec and sec.mfa_enrolled)


def start_enrolment(user):
    """New unconfirmed secret; returns {secret, otpauth_uri, qr_svg, qr_data_uri} (contract A6;
    qr_data_uri is the same SVG for an <img>, which is the safer way to render it)."""
    sec = security_for(user)
    sec.totp_secret = pyotp.random_base32(32)
    sec.totp_confirmed_at = None
    sec.totp_last_step = 0
    sec.save()
    uri = pyotp.TOTP(sec.totp_secret).provisioning_uri(name=user.get_username(), issuer_name=settings.MFA_ISSUER)
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue()
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
    return {"secret": sec.totp_secret, "otpauth_uri": uri, "qr_svg": svg.decode(), "qr_data_uri": data_uri}


def _check_totp(sec, code):
    """Accepts the current step +/- 1, never the same or an older step twice."""
    if not sec.totp_secret or not code or not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(sec.totp_secret)
    now_step = int(time.time()) // STEP
    for step in (now_step - 1, now_step, now_step + 1):
        if step > sec.totp_last_step and hmac.compare_digest(totp.at(step * STEP), code):
            sec.totp_last_step = step
            sec.save(update_fields=["totp_last_step"])
            return True
    return False


def confirm_enrolment(user, code):
    """Confirms the pending secret; returns the plain recovery codes (shown once) or None."""
    with transaction.atomic():
        sec = UserSecurity.objects.select_for_update().filter(user=user).first()
        if not sec or sec.mfa_enrolled or not _check_totp(sec, code):
            return None
        sec.totp_confirmed_at = timezone.now()
        sec.save(update_fields=["totp_confirmed_at"])
        return regenerate_recovery_codes(user)


def _hash(code):
    return hashlib.sha256(code.replace("-", "").replace(" ", "").lower().encode()).hexdigest()


def regenerate_recovery_codes(user):
    RecoveryCode.objects.filter(user=user).delete()
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = base64.b32encode(secrets.token_bytes(10)).decode().lower()  # 80 bits
        codes.append("-".join(raw[i:i + 4] for i in range(0, 16, 4)))
    RecoveryCode.objects.bulk_create(RecoveryCode(user=user, code_hash=_hash(c)) for c in codes)
    return codes


def verify_code(user, code):
    """True if `code` is a valid TOTP or an unused recovery code (which is then burnt)."""
    code = (code or "").strip()
    with transaction.atomic():
        sec = UserSecurity.objects.select_for_update().filter(user=user).first()
        if not sec or not sec.mfa_enrolled:
            return False
        if _check_totp(sec, code):
            return True
        if len(code.replace("-", "")) == 16:
            n = RecoveryCode.objects.filter(user=user, code_hash=_hash(code), used_at__isnull=True).update(
                used_at=timezone.now()
            )
            return n == 1
    return False


def reset(user):
    UserSecurity.objects.filter(user=user).update(totp_secret="", totp_confirmed_at=None, totp_last_step=0)  # nosec B106 (clears the secret)
    RecoveryCode.objects.filter(user=user).delete()


def mark_session_verified(session, user, method="totp"):
    """Marks a session as a completed CMS sign-in for `user` (method "totp", or "password" when MFA is off).
    Called by the login flow (and by the QA test harness after force_login). CMSSessionAuthentication rejects
    any session without this mark, so no other login path bypasses it."""
    session[SESSION_FLAG] = user.pk
    session[SESSION_METHOD] = method


def session_signed_in(session, user):
    """The one rule for "this session is a CMS sign-in for this user": the mark matches, and with MFA on the
    sign-in used a code (a password-only session from before MFA was switched on no longer counts)."""
    if session.get(SESSION_FLAG) != user.pk:
        return False
    return not settings.MFA_ENABLED or session.get(SESSION_METHOD) == "totp"


def is_verified(request):
    """True if this Django request has an active user whose session completed password + MFA."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    return session_signed_in(request.session, user)
