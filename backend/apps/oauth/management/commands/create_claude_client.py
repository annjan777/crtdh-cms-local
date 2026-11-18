"""Create (or rotate) the pre-registered OAuth client that Claude uses.

    python manage.py create_claude_client            # first time
    python manage.py create_claude_client --rotate   # new secret; old one stops working

Prints the client id and secret ONCE. The secret is stored hashed; it can't be shown again.
Paste both into claude.ai → Add custom connector → Advanced settings.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.generators import generate_client_id, generate_client_secret
from oauth2_provider.models import get_application_model

CLIENT_NAME = "Claude"


class Command(BaseCommand):
    help = "Create the pre-registered confidential OAuth client for the Claude connector and print its credentials once."

    def add_arguments(self, parser):
        parser.add_argument("--rotate", action="store_true", help="Issue a new secret for the existing client.")

    def handle(self, *args, rotate=False, **options):
        Application = get_application_model()
        redirect_uris = " ".join(settings.MCP_CLAUDE_REDIRECT_URIS)
        app = Application.objects.filter(name=CLIENT_NAME, user__isnull=True).first()
        if app and not rotate:
            raise CommandError(
                f"The Claude client already exists (client id {app.client_id}). "
                "Use --rotate to issue a new secret; existing connections keep working until their tokens expire."
            )
        secret = generate_client_secret()
        if app is None:
            app = Application(
                name=CLIENT_NAME,
                client_id=generate_client_id(),
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                skip_authorization=False,
            )
        app.redirect_uris = redirect_uris
        app.client_secret = secret  # hashed on save
        app.save()
        self.stdout.write("Claude connector OAuth client (shown once — store it in the password manager now):")
        self.stdout.write(f"  Client ID:     {app.client_id}")
        self.stdout.write(f"  Client secret: {secret}")
        self.stdout.write(f"  Redirect URIs: {redirect_uris}")
        self.stdout.write(f"  Server URL:    {settings.MCP_PUBLIC_URL}/mcp")
