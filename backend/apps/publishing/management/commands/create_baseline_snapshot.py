from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.publishing.models import Snapshot
from apps.publishing.snapshot import build_snapshot, canonical_json


class Command(BaseCommand):
    help = ("Record today's CMS content as the published baseline (once, at migration time) so the review screen "
            "shows only real edits and discard has something to revert to. Refuses if a published snapshot exists.")

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="record a new baseline even if one exists")

    def handle(self, *args, force=False, **options):
        import hashlib

        if Snapshot.last_published() and not force:
            self.stderr.write("A published snapshot already exists; use --force to add another baseline.")
            return
        data = build_snapshot(published_by="baseline")
        snap, _ = Snapshot.objects.get_or_create(
            snapshot_id=data["snapshot_id"],
            defaults={"data": data, "sha256": hashlib.sha256(canonical_json(data).encode()).hexdigest(),
                      "note": "baseline (content live before v3)"})
        snap.published_at = timezone.now()
        snap.save(update_fields=["published_at"])
        counts = ", ".join(f"{k} {len(v)}" for k, v in data["collections"].items())
        self.stdout.write(f"baseline {snap.snapshot_id}: {counts}")
