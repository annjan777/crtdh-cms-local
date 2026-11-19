"""URL patterns for the Claude connector.

- `oauth_urlpatterns`: mounted at /oauth/ on both the CMS origin (authorize, in the editor's
  browser) and the MCP host (token, revoke; Claude's servers).
- `wellknown_urlpatterns`: mounted at the MCP host root.
- `cms_api_urlpatterns`: mounted at /api/v1/cms/ on the CMS origin.
"""

from django.urls import include, path
from oauth2_provider import views as dot_views

from . import views
from .dcr import ClaudeOnlyDCRManagementView

_oauth = [
    path("authorize/", views.ConsentAuthorizationView.as_view(), name="authorize"),
    path("token/", dot_views.TokenView.as_view(), name="token"),
    path("revoke_token/", dot_views.RevokeTokenView.as_view(), name="revoke-token"),
    # DCR: the view 404s and the permission class refuses unless MCP_OAUTH_DCR_ENABLED.
    path("register/", dot_views.DynamicClientRegistrationView.as_view(), name="dcr-register"),
    path(
        "register/<str:client_id>/",
        ClaudeOnlyDCRManagementView.as_view(),
        name="dcr-register-management",
    ),
]

oauth_urlpatterns = [path("oauth/", include((_oauth, "oauth2_provider"), namespace="oauth2_provider"))]

wellknown_urlpatterns = [
    path(".well-known/oauth-authorization-server", views.authorization_server_metadata, name="oauth-as-metadata"),
    path(".well-known/oauth-protected-resource", views.protected_resource_metadata, name="oauth-pr-metadata"),
    path(".well-known/oauth-protected-resource/mcp", views.protected_resource_metadata, name="oauth-pr-metadata-mcp"),
]

cms_api_urlpatterns = [
    path("claude-access/", views.ClaudeAccessView.as_view(), name="claude-access"),
    path("claude-access/revoke/", views.ClaudeAccessRevokeView.as_view(), name="claude-access-revoke"),
    path("claude-access/new-secret/", views.ClaudeClientSecretView.as_view(), name="claude-access-new-secret"),
]
