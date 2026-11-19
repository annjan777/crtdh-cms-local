"""Create (or rotate) the pre-registered OAuth client that Claude uses.

    python manage.py create_claude_client            # first time
    python manage.py create_claude_client --rotate   # new secret; old one stops working

Prints the client id and secret ONCE. The secret is stored hashed; it can't be shown again.
Paste both into claude.ai → Add custom connector → Advanced settings.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.oauth.claude_client import get_claude_client, issue_secret, server_url

class Command(BaseCommand):
    help = "Create the pre-registered confidential OAuth client for the Claude connector and print its credentials once."

    def add_arguments(self, parser):
        parser.add_argument("--rotate", action="store_true", help="Issue a new secret for the existing client.")

    def handle(self, *args, rotate=False, **options):
        app = get_claude_client()
        if app and not rotate:
            raise CommandError(
                f"The Claude client already exists (client id {app.client_id}). "
                "Use --rotate to issue a new secret; existing connections keep working until their tokens expire."
            )
        app, secret = issue_secret()
        self.stdout.write("Claude connector OAuth client (shown once — store it in the password manager now):")
        self.stdout.write(f"  Client ID:     {app.client_id}")
        self.stdout.write(f"  Client secret: {secret}")
        self.stdout.write(f"  Redirect URIs: {' '.join(settings.MCP_CLAUDE_REDIRECT_URIS)}")
        self.stdout.write(f"  Server URL:    {server_url()}")
