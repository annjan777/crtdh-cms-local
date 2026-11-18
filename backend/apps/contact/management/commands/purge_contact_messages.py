"""Retention rule: delete contact messages older than CONTACT_RETENTION_DAYS (default 365).

Run daily (deploy/docker-compose.yml `purge` service). See docs/privacy-notice.md.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contact.models import ContactMessage


class Command(BaseCommand):
    help = "Delete contact messages older than the retention period."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=settings.CONTACT_RETENTION_DAYS)
        qs = ContactMessage.objects.filter(created_at__lt=cutoff)
        n = qs.count()
        if not opts["dry_run"]:
            qs.delete()
        self.stdout.write(f"{'Would delete' if opts['dry_run'] else 'Deleted'} {n} contact message(s) older than {cutoff:%Y-%m-%d}.")
