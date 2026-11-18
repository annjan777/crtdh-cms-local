from django.conf import settings
from django.db import models


class UserSecurity(models.Model):
    """Per-user MFA state. The TOTP secret is stored as-is (like django-otp);
    the database is private to the CMS zone and backed up encrypted."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="security")
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    totp_last_step = models.BigIntegerField(default=0)  # replay protection
    must_change_password = models.BooleanField(default=False)

    @property
    def mfa_enrolled(self):
        return bool(self.totp_secret and self.totp_confirmed_at)


class RecoveryCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64)  # sha256 hex of the normalised code
    used_at = models.DateTimeField(null=True, blank=True)


class UserSession(models.Model):
    """Maps a user to their Django session keys so all can be revoked."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cms_sessions")
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)


class AuthThrottle(models.Model):
    """Failed sign-in counters per username ("u:<name>") and per IP ("ip:<addr>")."""

    key = models.CharField(max_length=200, unique=True)
    failures = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
