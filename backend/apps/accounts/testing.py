"""Test helpers (imported only by tests; nothing in the app calls these)."""
from django.utils import timezone

from . import mfa


def enroll_totp_for_test(user):
    """Enrols TOTP without the confirm step; returns the base32 secret."""
    secret = mfa.start_enrolment(user)["secret"]
    user.security.totp_confirmed_at = timezone.now()
    user.security.save(update_fields=["totp_confirmed_at"])
    return secret
