"""OAuth 2.1 rules on top of django-oauth-toolkit for the Claude connector.

- Only the `cms.drafts` scope exists, and only the authorization-code grant (+ refresh).
- PKCE with S256 is mandatory (plain is refused by COMPLIANT_BCP_RFC9700_PKCE_METHOD; this
  class also refuses a missing method).
- A token is only issued or refreshed for an active CMS user who holds the editor role.
- A connection (one refresh-token family) lives at most MCP_OAUTH_MAX_GRANT_DAYS.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from oauth2_provider.models import get_refresh_token_model
from oauth2_provider.oauth2_validators import OAuth2Validator

from apps.accounts.roles import EDITOR, has_role

from .models import GrantFamily


def user_may_connect(user) -> bool:
    return bool(user and user.is_active and has_role(user, EDITOR))


class CmsOAuth2Validator(OAuth2Validator):
    def validate_grant_type(self, client_id, grant_type, client, request, *args, **kwargs):
        if grant_type not in ("authorization_code", "refresh_token"):
            return False
        return super().validate_grant_type(client_id, grant_type, client, request, *args, **kwargs)

    def validate_response_type(self, client_id, response_type, client, request, *args, **kwargs):
        if response_type != "code":
            return False
        return super().validate_response_type(client_id, response_type, client, request, *args, **kwargs)

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        allowed = {settings.MCP_OAUTH_SCOPE}
        return bool(scopes) and set(scopes) <= allowed

    def is_pkce_required(self, client_id, request):
        return True

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        if not super().validate_code(client_id, code, client, request, *args, **kwargs):
            return False
        return user_may_connect(request.user)

    def get_code_challenge_method(self, code, request):
        # /authorize already refuses "plain"; verifying every code_verifier as S256 means a
        # grant can never be redeemed with the plain method even if one slipped through.
        return "S256"

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        if not super().validate_refresh_token(refresh_token, client, request, *args, **kwargs):
            return False
        if not user_may_connect(request.user):
            return False
        family = getattr(request.refresh_token_instance, "token_family", None)
        if family is None:
            return False
        started = GrantFamily.objects.filter(token_family=family).values_list("created_at", flat=True).first()
        if started is None:
            return False
        return timezone.now() < started + timedelta(days=settings.MCP_OAUTH_MAX_GRANT_DAYS)

    def save_bearer_token(self, token, request, *args, **kwargs):
        super().save_bearer_token(token, request, *args, **kwargs)
        # First token of a new connection: remember when the family started.
        if getattr(request, "grant_type", None) == "authorization_code" and token.get("refresh_token"):
            rt = (
                get_refresh_token_model()
                .objects.filter(user=request.user, application=request.client)
                .order_by("-id")
                .first()
            )
            if rt is not None and rt.token_family:
                GrantFamily.objects.get_or_create(token_family=rt.token_family, defaults={"user": request.user})
