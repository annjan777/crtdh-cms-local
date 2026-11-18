"""TOTP MFA and recovery codes. `verify_code(user, code)` is the one check used
by the CMS login and the MCP OAuth authorize step."""
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
SESSION_FLAG = "crtdh_mfa_verified"  # set only after password + TOTP; checked on every request
STEP = 30


def security_for(user):
    sec, _ = UserSecurity.objects.get_or_create(user=user)
    return sec


def is_enrolled(user):
    sec = UserSecurity.objects.filter(user=user).first()
    return bool(sec and sec.mfa_enrolled)


def start_enrolment(user):
    """New unconfirmed secret; returns {secret, otpauth_uri, qr_data_uri}."""
    sec = security_for(user)
    sec.totp_secret = pyotp.random_base32(32)
    sec.totp_confirmed_at = None
    sec.totp_last_step = 0
    sec.save()
    uri = pyotp.TOTP(sec.totp_secret).provisioning_uri(name=user.get_username(), issuer_name=settings.MFA_ISSUER)
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"secret": sec.totp_secret, "otpauth_uri": uri, "qr_data_uri": data_uri}


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
    UserSecurity.objects.filter(user=user).update(totp_secret="", totp_confirmed_at=None, totp_last_step=0)
    RecoveryCode.objects.filter(user=user).delete()


def mark_session_verified(session, user):
    """Marks a session as having passed MFA for `user`. Called by the login flow
    (and by the QA test harness after force_login). CMSSessionAuthentication
    rejects any session without this flag, so no other login path bypasses MFA."""
    session[SESSION_FLAG] = user.pk
