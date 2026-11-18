import time

from django.core.management.base import BaseCommand

from apps.publishing.publish import run_once


class Command(BaseCommand):
    help = "Build queued publishes (snapshot -> media -> frontend build -> tarball). Loops unless --once."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="build at most one publish, then exit")
        parser.add_argument("--interval", type=float, default=3.0, help="seconds between polls")

    def handle(self, *args, once=False, interval=3.0, **options):
        while True:
            p = run_once()
            if p is not None:
                self.stdout.write(f"publish {p.id}: {p.status} ({p.step}) {p.message}")
            if once:
                return
            if p is None:
                time.sleep(interval)
