"""Housekeeping: drop sign-in failure counters that are unlocked and older than the reset window."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AuthThrottle


class Command(BaseCommand):
    help = "Delete stale sign-in failure counters."

    def handle(self, *args, **opts):
        now = timezone.now()
        cutoff = now - timedelta(seconds=settings.AUTH_LOCKOUT["RESET_AFTER_SECONDS"])
        n, _ = AuthThrottle.objects.filter(updated_at__lt=cutoff).filter(
            Q(locked_until__isnull=True) | Q(locked_until__lt=now)).delete()
        self.stdout.write(f"Deleted {n} stale sign-in counter(s).")
