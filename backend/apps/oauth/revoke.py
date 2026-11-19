"""Revoke every Claude-connector credential a CMS user holds."""

import logging

from django.db import transaction
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_grant_model, get_refresh_token_model

from .models import GrantFamily

log = logging.getLogger(__name__)


@transaction.atomic
def revoke_all_for_user(user, *, reason: str) -> int:
    """Delete the user's access tokens and authorization codes and revoke their refresh
    tokens. Takes effect on the very next MCP request (the bearer check reads the DB on
    every request). Returns how many credentials were cut."""
    AccessToken = get_access_token_model()
    RefreshToken = get_refresh_token_model()
    Grant = get_grant_model()
    now = timezone.now()
    refresh = RefreshToken.objects.filter(user=user, revoked__isnull=True).update(revoked=now)
    access, _ = AccessToken.objects.filter(user=user).delete()
    grants, _ = Grant.objects.filter(user=user).delete()
    GrantFamily.objects.filter(user=user).delete()
    total = refresh + access + grants
    # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure -- logs a count and a user id, no token values
    log.info("Revoked %s Claude connector credentials for user %s (%s)", total, user.pk, reason)
    return total


def active_connections(user):
    """Unrevoked refresh tokens = live Claude connections (one per connect)."""
    return (
        get_refresh_token_model()
        .objects.filter(user=user, revoked__isnull=True)
        .select_related("application")
        .order_by("-created")
    )
