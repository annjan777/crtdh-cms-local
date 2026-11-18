import json

from django.core.management.base import BaseCommand

from apps.publishing.registry import export_registry


class Command(BaseCommand):
    help = "Print the section registry (contract §2) as JSON: manage.py export_registry > registry.json"

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(export_registry(), indent=2, ensure_ascii=False))
