"""Settings for the Claude MCP server and its OAuth 2.1 authorization server (WS4).

Imported at the end of config/settings.py. Everything here can be overridden with
environment variables of the same name. See docs/mcp.md.
"""

import environ as _environ

_env = _environ.Env()

MCP_INSTALLED_APPS = [
    "oauth2_provider",
    "apps.oauth",
    "mcp_server",
]

# Public base URLs (no trailing slash).
# MCP_PUBLIC_URL: the hostname Claude reaches through the tunnel; serves /mcp, the
#   /.well-known metadata and the token endpoint. Limited to Anthropic's IP range at the edge.
# CMS_PUBLIC_URL: the CMS origin (behind Cloudflare Access) that editors open in their
#   browser. The OAuth sign-in/consent page lives here, because an editor's browser is not
#   in Anthropic's IP range and so cannot reach the MCP hostname.
MCP_PUBLIC_URL = _env("MCP_PUBLIC_URL", default="http://localhost:8400").rstrip("/")
CMS_PUBLIC_URL = _env("CMS_PUBLIC_URL", default="http://localhost:8000").rstrip("/")
MCP_OAUTH_AUTHORIZE_URL = _env("MCP_OAUTH_AUTHORIZE_URL", default=f"{CMS_PUBLIC_URL}/oauth/authorize/")

# Sign-in page of the CMS (backend-security). The authorize view sends signed-out users
# (or users who have not completed MFA) here with ?next=<the authorize URL>.
CMS_LOGIN_URL = _env("CMS_LOGIN_URL", default="/cms/login")
# Never turn this off outside a developer laptop: the consent screen requires a CMS
# session that completed TOTP MFA.
MCP_OAUTH_REQUIRE_MFA = _env.bool("MCP_OAUTH_REQUIRE_MFA", default=True)

# Redirect URIs registered for the pre-registered Claude client (verified 19 Nov 2026
# against claude.com/docs/connectors/building/authentication).
MCP_CLAUDE_REDIRECT_URIS = _env.list(
    "MCP_CLAUDE_REDIRECT_URIS",
    default=[
        "https://claude.ai/api/mcp/auth_callback",
        "https://claude.com/api/mcp/auth_callback",
    ],
)
# Dynamic Client Registration (RFC 7591). Off: staff paste the pre-registered client id and
# secret into the connector's Advanced settings. When on, registrations are limited to the
# redirect URIs above.
MCP_OAUTH_DCR_ENABLED = _env.bool("MCP_OAUTH_DCR_ENABLED", default=False)

MCP_OAUTH_SCOPE = "cms.drafts"
MCP_ACCESS_TOKEN_SECONDS = _env.int("MCP_ACCESS_TOKEN_SECONDS", default=3600)
# Absolute lifetime of one connection (consent → last refresh). After this the editor
# reconnects (signs in with MFA again).
MCP_OAUTH_MAX_GRANT_DAYS = _env.int("MCP_OAUTH_MAX_GRANT_DAYS", default=30)

# Guardrails (PLAN WS4.5)
CMS_SESSION_LIMIT = _env.int("CMS_SESSION_LIMIT", default=25)  # changes per connector session
MCP_RATE_LIMIT_PER_MINUTE = _env.int("MCP_RATE_LIMIT_PER_MINUTE", default=60)  # all tool calls, per user
MCP_WRITE_RATE_LIMIT_PER_MINUTE = _env.int("MCP_WRITE_RATE_LIMIT_PER_MINUTE", default=20)  # writes, per user

# upload_image_from_url (SSRF-hardened fetcher). Host patterns: "example.org" matches
# exactly, "*.example.org" matches any subdomain (not the apex).
MCP_FETCH_ALLOWED_HOSTS = _env.list("MCP_FETCH_ALLOWED_HOSTS", default=["iitkgp.ac.in", "*.iitkgp.ac.in"])
MCP_FETCH_MAX_BYTES = _env.int("MCP_FETCH_MAX_BYTES", default=10 * 1024 * 1024)
MCP_FETCH_TIMEOUT_SECONDS = _env.float("MCP_FETCH_TIMEOUT_SECONDS", default=10.0)

# MCP protocol revisions this server accepts (pinned; see docs/mcp.md). Requests that
# declare any other MCP-Protocol-Version are refused before they reach the SDK.
MCP_PROTOCOL_VERSIONS = ["2025-06-18", "2025-11-25"]
# Extra Host header values /mcp accepts besides MCP_PUBLIC_URL's (e.g. "127.0.0.1:8400" for local tests).
MCP_EXTRA_ALLOWED_HOSTS = _env.list("MCP_EXTRA_ALLOWED_HOSTS", default=[])

OAUTH2_PROVIDER = {
    "SCOPES": {MCP_OAUTH_SCOPE: "Edit website content as unpublished drafts"},
    "DEFAULT_SCOPES": [MCP_OAUTH_SCOPE],
    "PKCE_REQUIRED": True,
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https"],
    "ALLOW_URI_WILDCARDS": False,
    "AUTHORIZATION_CODE_EXPIRE_SECONDS": 60,
    "ACCESS_TOKEN_EXPIRE_SECONDS": MCP_ACCESS_TOKEN_SECONDS,
    "REFRESH_TOKEN_EXPIRE_SECONDS": MCP_OAUTH_MAX_GRANT_DAYS * 86400,
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,
    "REFRESH_TOKEN_GRACE_PERIOD_SECONDS": 0,  # required by hashed token storage
    "REQUEST_APPROVAL_PROMPT": "force",
    "OAUTH2_VALIDATOR_CLASS": "apps.oauth.validators.CmsOAuth2Validator",
    "DCR_ENABLED": MCP_OAUTH_DCR_ENABLED,
    "DCR_REGISTRATION_PERMISSION_CLASSES": ("apps.oauth.dcr.ClaudeOnlyDCRPermission",),
    "CIMD_ENABLED": False,
    # RFC 9700 behaviour gates: plain PKCE refused, tokens stored only as SHA-256
    # checksums, tokens never accepted in query strings, `iss` in authorization responses.
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,
    "COMPLIANT_BCP_RFC9700_REFRESH_TOKEN": True,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_SCHEME": True,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_MATCHING": True,
    "COMPLIANT_BCP_RFC9700_PKCE_REQUIRED": True,
    "OIDC_ISS_ENDPOINT": MCP_PUBLIC_URL,
}
