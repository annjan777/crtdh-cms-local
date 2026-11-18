"""OAuth endpoints for the Claude connector and the CMS endpoints that manage it."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from oauth2_provider.views import AuthorizationView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.roles import ADMIN, IsEditor, has_role, user_roles

from .mfa import session_has_mfa
from .revoke import active_connections, revoke_all_for_user
from .validators import user_may_connect

ROLE_LABELS = {"editor": "Editor", "publisher": "Publisher", "admin": "Admin"}


def role_label(user) -> str:
    roles = user_roles(user)
    return ROLE_LABELS.get(roles[-1], "") if roles else ""


def display_name(user) -> str:
    return (user.get_full_name() or user.get_username()).strip()


class ConsentAuthorizationView(AuthorizationView):
    """/oauth/authorize/ — runs in the editor's browser on the CMS origin.

    Requires a CMS session that completed MFA (otherwise: CMS sign-in, then back here),
    an active account with the editor role, and an explicit "Allow" on every connect.
    """

    template_name = "oauth/consent.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not session_has_mfa(request):
            return redirect_to_login(request.get_full_path(), settings.CMS_LOGIN_URL, "next")
        if not user_may_connect(request.user):
            return render(request, "oauth/not_allowed.html", status=403)
        if "approval_prompt" in request.GET:
            # Consent is shown on every connect; a client can't ask to skip it.
            request.GET = request.GET.copy()
            request.GET.pop("approval_prompt")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cms_user_name"] = display_name(self.request.user)
        context["cms_user_role"] = role_label(self.request.user)
        return context


def _json(data):
    response = JsonResponse(data)
    response["Cache-Control"] = "public, max-age=300"
    return response


def _auth_methods():
    methods = ["client_secret_basic", "client_secret_post"]
    if settings.MCP_OAUTH_DCR_ENABLED:
        methods.append("none")
    return methods


@require_GET
def authorization_server_metadata(request):
    """RFC 8414. The issuer is the MCP hostname; the authorization endpoint is on the CMS
    origin (see docs/mcp.md, "Why the sign-in page is on the CMS host")."""
    issuer = settings.MCP_PUBLIC_URL
    data = {
        "issuer": issuer,
        "authorization_endpoint": settings.MCP_OAUTH_AUTHORIZE_URL,
        "token_endpoint": f"{issuer}/oauth/token/",
        "revocation_endpoint": f"{issuer}/oauth/revoke_token/",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": _auth_methods(),
        "revocation_endpoint_auth_methods_supported": _auth_methods(),
        "scopes_supported": [settings.MCP_OAUTH_SCOPE],
        "authorization_response_iss_parameter_supported": True,
        "client_id_metadata_document_supported": False,
    }
    if settings.MCP_OAUTH_DCR_ENABLED:
        data["registration_endpoint"] = f"{issuer}/oauth/register/"
    return _json(data)


@require_GET
def protected_resource_metadata(request):
    """RFC 9728, for the resource https://<mcp host>/mcp."""
    return _json(
        {
            "resource": f"{settings.MCP_PUBLIC_URL}/mcp",
            "authorization_servers": [settings.MCP_PUBLIC_URL],
            "scopes_supported": [settings.MCP_OAUTH_SCOPE],
            "bearer_methods_supported": ["header"],
            "resource_name": "CRTDH website CMS (unpublished changes only)",
        }
    )


def _error(code, message, fix, http_status):
    return Response(
        {
            "code": code,
            "message": message,
            "fix": fix,
            "retryable": False,
            "side_effects": "none",
            "field": None,
            "current_version": None,
            "request_id": None,
        },
        status=http_status,
    )


class ClaudeAccessView(APIView):
    """GET /api/v1/cms/claude-access/ — the signed-in user's live Claude connections."""

    permission_classes = [IsEditor]

    def get(self, request):
        rows = [
            {"client": rt.application.name, "connected_at": rt.created.isoformat()}
            for rt in active_connections(request.user)
        ]
        return Response({"connected": bool(rows), "connections": rows})


class ClaudeAccessRevokeView(APIView):
    """POST /api/v1/cms/claude-access/revoke/ — {} revokes your own Claude access;
    {"user_id": n} (admins only) revokes someone else's. Effective on Claude's next call."""

    permission_classes = [IsEditor]

    def post(self, request):
        target = request.user
        user_id = request.data.get("user_id") if hasattr(request.data, "get") else None
        if user_id not in (None, "", request.user.pk):
            if not has_role(request.user, ADMIN):
                return _error(
                    "CMS_FORBIDDEN_ROLE",
                    "Only an Admin can disconnect Claude for another person.",
                    "Ask an Admin, or omit user_id to disconnect your own access.",
                    status.HTTP_403_FORBIDDEN,
                )
            try:
                target = get_user_model().objects.get(pk=int(user_id))
            except (ValueError, TypeError, get_user_model().DoesNotExist):
                return _error(
                    "CMS_NOT_FOUND", "No CMS user with that id.", "Check the user id.", status.HTTP_404_NOT_FOUND
                )
        revoked = revoke_all_for_user(target, reason=f"revoked from CMS by user {request.user.pk}")
        return Response({"revoked": revoked, "user_id": target.pk})
