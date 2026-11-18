"""Cut Claude access the moment a CMS user is deactivated."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .revoke import revoke_all_for_user

User = get_user_model()

try:  # backend-security's explicit signal (preferred)
    from apps.accounts.signals import user_deactivated  # type: ignore
except ImportError:  # TODO(integration, backend-security): signal lands with their merge
    user_deactivated = None


if user_deactivated is not None:  # pragma: no cover - exercised after backend-security merges

    @receiver(user_deactivated, dispatch_uid="cms_oauth_revoke_on_deactivate_signal")
    def _on_user_deactivated(sender, user=None, **kwargs):
        if user is not None:
            revoke_all_for_user(user, reason="user_deactivated signal")


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
