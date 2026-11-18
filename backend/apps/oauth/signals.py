"""Cut Claude access the moment a CMS user is deactivated."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .revoke import revoke_all_for_user

User = get_user_model()

# backend-security's signals (apps/accounts/signals.py), both sent as (sender=User, user=<User>):
#   user_deactivated       account switched off
#   user_sessions_revoked  password reset/change, MFA reset, "sign out everywhere", deactivation
# Either one must also cut Claude's tokens, or a recovered account's connector keeps write access.
REVOKING_SIGNALS = ("user_deactivated", "user_sessions_revoked")


def _revoke_receiver(sender, user=None, signal=None, **kwargs):
    if user is not None:
        name = next((n for n in REVOKING_SIGNALS if getattr(_signals_module, n, None) is signal), "account signal")
        revoke_all_for_user(user, reason=name)


_signals_module = None


def connect_account_signals(module) -> list[str]:
    """Connect revocation to whichever of REVOKING_SIGNALS `module` provides."""
    global _signals_module
    _signals_module = module
    connected = []
    for name in REVOKING_SIGNALS:
        sig = getattr(module, name, None)
        if sig is not None:
            sig.connect(_revoke_receiver, dispatch_uid=f"cms_oauth_revoke_on_{name}", weak=False)
            connected.append(name)
    return connected


try:
    from apps.accounts import signals as _account_signals  # type: ignore
except ImportError:  # TODO(integration, backend-security): present after their merge
    _account_signals = None
if _account_signals is not None:
    connect_account_signals(_account_signals)


# Fallback that also covers deactivation through the Django admin, a shell or a bulk
# script that calls save(): compare is_active before and after the save.
@receiver(pre_save, sender=User, dispatch_uid="cms_oauth_track_is_active")
def _remember_previous_active(sender, instance, **kwargs):
    if instance.pk:
        instance._cms_oauth_was_active = (
            sender.objects.filter(pk=instance.pk).values_list("is_active", flat=True).first()
        )


@receiver(post_save, sender=User, dispatch_uid="cms_oauth_revoke_on_inactive_save")
def _revoke_when_inactive(sender, instance, created, **kwargs):
    if not created and not instance.is_active and getattr(instance, "_cms_oauth_was_active", False):
        revoke_all_for_user(instance, reason="is_active set to False")
