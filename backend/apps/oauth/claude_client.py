"""The one pre-registered OAuth client the Claude connector uses (shared by the CLI and the CMS screen)."""

from django.conf import settings
from oauth2_provider.generators import generate_client_id, generate_client_secret
from oauth2_provider.models import get_application_model

CLIENT_NAME = "Claude"


def get_claude_client():
    return get_application_model().objects.filter(name=CLIENT_NAME, user__isnull=True).first()


def server_url():
    return f"{settings.MCP_PUBLIC_URL}/mcp"


def issue_secret():
    """Create the client, or give the existing one a new secret. Returns (app, secret); the secret is stored
    hashed and can't be shown again. Connections already made keep working until their tokens expire; Claude
    needs the new secret in the connector to connect again."""
    Application = get_application_model()
    app = get_claude_client()
    secret = generate_client_secret()
    if app is None:
        app = Application(
            name=CLIENT_NAME,
            client_id=generate_client_id(),
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            skip_authorization=False,
        )
    app.redirect_uris = " ".join(settings.MCP_CLAUDE_REDIRECT_URIS)
    app.client_secret = secret  # hashed on save
    app.save()
    return app, secret
