"""Dynamic Client Registration policy (only used when MCP_OAUTH_DCR_ENABLED is on)."""

import json

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.views import DynamicClientRegistrationManagementView


def redirect_uris_allowed(data) -> bool:
    if not isinstance(data, dict):
        return False
    uris = data.get("redirect_uris")
    return isinstance(uris, list) and bool(uris) and set(uris) <= set(settings.MCP_CLAUDE_REDIRECT_URIS)


class ClaudeOnlyDCRPermission:
    """Anonymous registration, but only for clients whose redirect URIs are Claude's own
    callbacks and that ask for the authorization-code grant. Anything else gets 403, so DCR
    can't be used to mint clients that redirect codes elsewhere."""

    def has_permission(self, request) -> bool:
        if not getattr(settings, "MCP_OAUTH_DCR_ENABLED", False):
            return False
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            return False
        if not isinstance(data, dict):
            return False
        if not redirect_uris_allowed(data):
            return False
        grants = set(data.get("grant_types") or ["authorization_code"])
        return grants <= {"authorization_code", "refresh_token"}


@method_decorator(csrf_exempt, name="dispatch")
class ClaudeOnlyDCRManagementView(DynamicClientRegistrationManagementView):
    """RFC 7592 management, but a registered client can't PUT its redirect_uris to anything
    other than Claude's callbacks (django-oauth-toolkit's put() doesn't run the
    registration permission classes)."""

    def put(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            data = None
        if not redirect_uris_allowed(data):
            return JsonResponse({"error": "invalid_redirect_uri",
                                 "error_description": "Only Claude's callback URLs can be registered."}, status=400)
        return super().put(request, *args, **kwargs)
