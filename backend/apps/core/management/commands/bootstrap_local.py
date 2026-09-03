"""One-shot local/dev bootstrap: makes a fresh `docker compose up` (or a
fresh local checkout) come up with the real, already-migrated CRTDH content
instead of an empty database and an empty media volume.

Two things ship inside the backend image for this to work with no external
dependencies (no scraped mirror, no network call):

- `apps/core/fixtures/local_seed.json` — a `dumpdata` snapshot of every
  content app (core, carousel, common, team, facilities, services,
  innovations, products, enterprises, media_gallery). Loading it is
  idempotent: Django's `loaddata` upserts by primary key, so re-running this
  command on every container start (as docker-compose.local.yml does) is
  safe and just re-syncs to the same state.
- `seed_media/` — a snapshot of MEDIA_ROOT at the time the fixture was
  taken. Every file in it that doesn't already exist at the matching path
  under MEDIA_ROOT is copied in, on every startup. Existing files are never
  touched — so media a staff member has since uploaded/edited through the
  admin is safe, and so is anything already seeded from an earlier image —
  but a later image that bundles new seed_media files (e.g. after a content
  update) still gets them copied into an already-populated volume instead
  of being silently skipped.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load the bundled local seed fixture and seed media (safe to run on every startup)."

    def handle(self, *args, **options):
        self._seed_media()
        self._load_fixture()

    def _seed_media(self):
        media_root = Path(settings.MEDIA_ROOT)
        seed_media = Path(settings.BASE_DIR) / "seed_media"

        if not seed_media.exists():
            self.stdout.write(self.style.WARNING("No seed_media/ bundled in this image — skipping media seed."))
            return

        media_root.mkdir(parents=True, exist_ok=True)

        copied = 0
        for src in seed_media.rglob("*"):
            if src.is_dir():
                continue
            dest = media_root / src.relative_to(seed_media)
            if dest.exists():
                continue  # never touch existing/staff-uploaded media
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1

        if copied:
            self.stdout.write(self.style.SUCCESS(f"Seeded {copied} new media file(s) into {media_root}."))
        else:
            self.stdout.write("MEDIA_ROOT already has every bundled seed file — nothing to add.")

    def _load_fixture(self):
        fixture = Path(settings.BASE_DIR) / "apps" / "core" / "fixtures" / "local_seed.json"
        if not fixture.exists():
            self.stdout.write(self.style.WARNING("No local_seed.json bundled in this image — skipping data seed."))
            return

        self.stdout.write("Loading local_seed.json ...")
        call_command("loaddata", str(fixture))
        self.stdout.write(self.style.SUCCESS("Data seeded."))
