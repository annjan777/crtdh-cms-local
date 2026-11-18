"""Dynamic Client Registration policy (only used when MCP_OAUTH_DCR_ENABLED is on)."""

import json

from django.conf import settings


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
        uris = data.get("redirect_uris")
        if not isinstance(uris, list) or not uris:
            return False
        if not set(uris) <= set(settings.MCP_CLAUDE_REDIRECT_URIS):
            return False
        grants = set(data.get("grant_types") or ["authorization_code"])
        return grants <= {"authorization_code", "refresh_token"}
