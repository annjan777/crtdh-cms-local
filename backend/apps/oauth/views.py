"""OAuth endpoints for the Claude connector and the CMS endpoints that manage it."""

from urllib.parse import urlsplit

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

from .mfa import must_change_password, session_has_mfa
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
        response = self._dispatch(request, *args, **kwargs)
        response["Content-Security-Policy"] = consent_csp(request)
        return response

    def _dispatch(self, request, *args, **kwargs):
        if (not request.user.is_authenticated or not session_has_mfa(request)
                or must_change_password(request.user)):
            # Signed out, MFA not done, or a temporary password still to change: /cms/login
            # sorts that out and sends the user back here.
            return redirect_to_login(request.get_full_path(), settings.CMS_LOGIN_URL, "next")
        if not user_may_connect(request.user):
            return render(request, "oauth/not_allowed.html", status=403)
        params = request.POST if request.method == "POST" else request.GET
        if params.get("code_challenge_method") != "S256" or not params.get("code_challenge"):
            # PKCE with S256 only (OAuth 2.1). Shown here rather than redirected: the
            # request isn't trustworthy enough to send anything to its redirect_uri.
            return render(request, "oauth/consent.html", {
                "error": {"error": "invalid_request",
                          "description": "This connection request is missing PKCE (S256)."}}, status=400)
        if "approval_prompt" in request.GET:
            # Consent is shown on every connect; a client can't ask to skip it.
            request.GET = request.GET.copy()
            request.GET.pop("approval_prompt")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cms_user_name"] = display_name(self.request.user)
        context["cms_user_role"] = role_label(self.request.user)
        # Show where the approval goes, so a look-alike client is noticeable.
        context["redirect_host"] = urlsplit(context.get("redirect_uri") or "").hostname or ""
        return context


DEFAULT_CSP = ("default-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; "
               "font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def _origin(uri: str) -> str | None:
    parts = urlsplit(uri)
    if parts.scheme != "https" or not parts.hostname:
        return None
    return f"https://{parts.netloc}"


def consent_csp(request) -> str:
    """The CMS policy, but form-action also allows the registered redirect origins of the
    client being authorised (Chrome applies form-action to the 302 that follows the consent
    POST, so 'self' alone blocks the return to claude.ai). Never widened globally."""
    from oauth2_provider.models import get_application_model

    client_id = (request.POST.get("client_id") if request.method == "POST" else None) or request.GET.get("client_id")
    uris = []
    if client_id:
        app = get_application_model().objects.filter(client_id=str(client_id)[:100]).first()
        if app is not None:
            uris = app.redirect_uris.split()
    origins = sorted({o for o in map(_origin, uris) if o})
    base = getattr(settings, "CONTENT_SECURITY_POLICY", None) or DEFAULT_CSP
    directives = [d.strip() for d in base.split(";") if d.strip() and not d.strip().startswith("form-action")]
    directives.append(" ".join(["form-action 'self'", *origins]))
    return "; ".join(directives)


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
        raw_id = request.data.get("user_id") if hasattr(request.data, "get") else None
        if raw_id not in (None, ""):
            try:
                user_id = int(raw_id)
            except (TypeError, ValueError):
                return _error("CMS_VALIDATION", "user_id must be a whole number.", "Send the CMS user's id.",
                              status.HTTP_400_BAD_REQUEST)
            if user_id != request.user.pk:
                if not has_role(request.user, ADMIN):
                    return _error(
                        "CMS_FORBIDDEN_ROLE",
                        "Only an Admin can disconnect Claude for another person.",
                        "Ask an Admin, or omit user_id to disconnect your own access.",
                        status.HTTP_403_FORBIDDEN,
                    )
                target = get_user_model().objects.filter(pk=user_id).first()
                if target is None:
                    return _error("CMS_NOT_FOUND", "No CMS user with that id.", "Check the user id.",
                                  status.HTTP_404_NOT_FOUND)
        revoked = revoke_all_for_user(target, reason=f"revoked from CMS by user {request.user.pk}")
        return Response({"revoked": revoked, "user_id": target.pk})
