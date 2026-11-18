"""OAuth 2.1 authorization server for the Claude connector (django-oauth-toolkit)."""

import base64
import hashlib
import io
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken
from rest_framework.test import APIClient

from apps.oauth.mfa import SESSION_FLAG
from apps.oauth.models import GrantFamily

from .conftest import issue_token, make_user

pytestmark = [pytest.mark.django_db, pytest.mark.security]

CALLBACK = "https://claude.ai/api/mcp/auth_callback"
CONSENT_FORM = b'name="allow"'


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def signed_in(user, mfa=True) -> Client:
    client = Client()
    client.force_login(user)
    if mfa:
        session = client.session
        session[SESSION_FLAG] = user.pk
        session.save()
    return client


def authorize_params(app, challenge, **extra):
    params = {"response_type": "code", "client_id": app.client_id, "redirect_uri": CALLBACK,
              "scope": "cms.drafts", "state": "st-123", "code_challenge": challenge,
              "code_challenge_method": "S256"}
    params.update(extra)
    return {k: v for k, v in params.items() if v is not None}


def get_code(client, app, challenge, **extra):
    params = authorize_params(app, challenge, **extra)
    page = client.get("/oauth/authorize/", params)
    assert page.status_code == 200, page.content[:400]
    form = {**params, "allow": "Authorize"}
    resp = client.post("/oauth/authorize/", form)
    assert resp.status_code == 302, resp.content[:400]
    location = urlsplit(resp["Location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == CALLBACK
    return parse_qs(location.query)


def basic(app):
    return "Basic " + base64.b64encode(f"{app.client_id}:test-secret-value".encode()).decode()


def exchange(app, code, verifier):
    return Client().post("/oauth/token/", {"grant_type": "authorization_code", "code": code,
                                           "redirect_uri": CALLBACK, "code_verifier": verifier},
                         HTTP_AUTHORIZATION=basic(app))


# ---------------------------------------------------------------- metadata
def test_authorization_server_metadata():
    import json

    from django.test import RequestFactory

    from apps.oauth.views import authorization_server_metadata

    data = json.loads(authorization_server_metadata(RequestFactory().get("/")).content)
    assert data["issuer"] == "http://localhost:8400"
    assert data["authorization_endpoint"] == "https://cms.example.org/oauth/authorize/"
    assert data["token_endpoint"] == "http://localhost:8400/oauth/token/"
    assert data["revocation_endpoint"] == "http://localhost:8400/oauth/revoke_token/"
    assert data["code_challenge_methods_supported"] == ["S256"]
    assert data["grant_types_supported"] == ["authorization_code", "refresh_token"]
    assert data["response_types_supported"] == ["code"]
    assert data["scopes_supported"] == ["cms.drafts"]
    assert "none" not in data["token_endpoint_auth_methods_supported"]
    assert "registration_endpoint" not in data


def test_protected_resource_metadata():
    import json

    from django.test import RequestFactory

    from apps.oauth.views import protected_resource_metadata

    data = json.loads(protected_resource_metadata(RequestFactory().get("/")).content)
    assert data["resource"] == "http://localhost:8400/mcp"
    assert data["authorization_servers"] == ["http://localhost:8400"]
    assert data["scopes_supported"] == ["cms.drafts"]
    assert data["bearer_methods_supported"] == ["header"]


# ---------------------------------------------------------------- authorize: who may consent
def test_authorize_requires_sign_in(claude_app):
    _, challenge = pkce()
    resp = Client().get("/oauth/authorize/", authorize_params(claude_app, challenge))
    assert resp.status_code == 302
    assert resp["Location"].startswith("/cms/login?next=")
    assert resp["Location"].startswith("/cms/login?next=/oauth/authorize/%3F")
    assert "code_challenge_method%3DS256" in resp["Location"]


def test_authorize_requires_mfa_completed_session(editor, claude_app):
    _, challenge = pkce()
    resp = signed_in(editor, mfa=False).get("/oauth/authorize/", authorize_params(claude_app, challenge))
    assert resp.status_code == 302 and resp["Location"].startswith("/cms/login")


def test_mfa_flag_for_another_user_does_not_count(editor, claude_app):
    other = make_user("other")
    client = signed_in(editor, mfa=False)
    session = client.session
    session[SESSION_FLAG] = other.pk
    session.save()
    _, challenge = pkce()
    assert client.get("/oauth/authorize/", authorize_params(claude_app, challenge)).status_code == 302


def test_user_without_role_cannot_connect(claude_app):
    nobody = make_user("norole", role=None)
    _, challenge = pkce()
    resp = signed_in(nobody).get("/oauth/authorize/", authorize_params(claude_app, challenge))
    assert resp.status_code == 403
    assert b"can't connect Claude" in resp.content


def test_consent_screen_names_user_and_role(editor, claude_app):
    _, challenge = pkce()
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(claude_app, challenge))
    assert resp.status_code == 200
    assert "Allow Claude to edit drafts as Priya Das (Editor)?" in resp.content.decode()


def test_approval_prompt_auto_cannot_skip_consent(editor, claude_app):
    issue_token(editor, claude_app)
    _, challenge = pkce()
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(claude_app, challenge, approval_prompt="auto"))
    assert resp.status_code == 200 and b"Allow Claude" in resp.content


# ---------------------------------------------------------------- authorize: request validation
def test_pkce_is_required(editor, claude_app):
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(
        claude_app, None, code_challenge_method=None))
    assert resp.status_code in (200, 302, 400)
    assert CONSENT_FORM not in resp.content
    if resp.status_code == 302:
        assert "code=" not in resp["Location"] and "error=" in resp["Location"]


def test_plain_pkce_is_refused(editor, claude_app):
    client = signed_in(editor)
    for method in ("plain", None):
        params = authorize_params(claude_app, "x" * 50, code_challenge_method=method)
        resp = client.get("/oauth/authorize/", params)
        assert resp.status_code == 400 and CONSENT_FORM not in resp.content
        # a tampered hidden form field can't downgrade either
        resp = client.post("/oauth/authorize/", {**params, "allow": "Authorize"})
        assert resp.status_code == 400 and "code=" not in resp.get("Location", "")


def test_wrong_redirect_uri_is_rejected_without_redirecting(editor, claude_app):
    _, challenge = pkce()
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(
        claude_app, challenge, redirect_uri="https://evil.example.com/cb"))
    assert resp.status_code != 302 or "evil.example.com" not in resp.get("Location", "")
    assert CONSENT_FORM not in resp.content


def test_other_scopes_are_refused(editor, claude_app):
    _, challenge = pkce()
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(claude_app, challenge, scope="cms.drafts users"))
    assert CONSENT_FORM not in resp.content


def test_cancel_returns_access_denied(editor, claude_app):
    _, challenge = pkce()
    client = signed_in(editor)
    params = authorize_params(claude_app, challenge)
    client.get("/oauth/authorize/", params)
    resp = client.post("/oauth/authorize/", params)
    assert resp.status_code == 302 and "error=access_denied" in resp["Location"]


# ---------------------------------------------------------------- token endpoint
def test_full_flow_issues_short_lived_access_and_refresh(editor, claude_app):
    verifier, challenge = pkce()
    query = get_code(signed_in(editor), claude_app, challenge)
    assert query["state"] == ["st-123"]
    assert query["iss"] == ["http://localhost:8400"]  # RFC 9207
    resp = exchange(claude_app, query["code"][0], verifier)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["scope"] == "cms.drafts"
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] <= 3600
    assert body["refresh_token"]
    # tokens are stored only as checksums
    stored = AccessToken.objects.get(user=editor)
    assert stored.token == "" and stored.token_checksum == hashlib.sha256(body["access_token"].encode()).hexdigest()
    assert GrantFamily.objects.filter(user=editor).count() == 1


def test_code_is_single_use_and_bound_to_verifier(editor, claude_app):
    verifier, challenge = pkce()
    code = get_code(signed_in(editor), claude_app, challenge)["code"][0]
    assert exchange(claude_app, code, "wrong-" + verifier).status_code == 400
    verifier2, challenge2 = pkce()
    code2 = get_code(signed_in(editor), claude_app, challenge2)["code"][0]
    assert exchange(claude_app, code2, verifier2).status_code == 200
    assert exchange(claude_app, code2, verifier2).status_code == 400


def test_token_requires_client_secret(editor, claude_app):
    verifier, challenge = pkce()
    code = get_code(signed_in(editor), claude_app, challenge)["code"][0]
    resp = Client().post("/oauth/token/", {"grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK,
                                           "code_verifier": verifier, "client_id": claude_app.client_id})
    assert resp.status_code == 401


def _tokens(editor, claude_app):
    verifier, challenge = pkce()
    code = get_code(signed_in(editor), claude_app, challenge)["code"][0]
    return exchange(claude_app, code, verifier).json()


def refresh(app, token):
    return Client().post("/oauth/token/", {"grant_type": "refresh_token", "refresh_token": token},
                         HTTP_AUTHORIZATION=basic(app))


def test_refresh_rotates_and_old_token_is_dead(editor, claude_app):
    first = _tokens(editor, claude_app)
    second = refresh(claude_app, first["refresh_token"])
    assert second.status_code == 200
    assert second.json()["refresh_token"] != first["refresh_token"]
    reuse = refresh(claude_app, first["refresh_token"])
    assert reuse.status_code == 400 and reuse.json()["error"] == "invalid_grant"


def test_connection_ends_after_30_days_however_often_refreshed(editor, claude_app):
    tokens = _tokens(editor, claude_app)
    GrantFamily.objects.filter(user=editor).update(created_at=timezone.now() - timedelta(days=31))
    resp = refresh(claude_app, tokens["refresh_token"])
    assert resp.status_code == 400 and resp.json()["error"] == "invalid_grant"


def test_refresh_refused_once_role_removed(editor, claude_app):
    tokens = _tokens(editor, claude_app)
    editor.groups.clear()
    assert refresh(claude_app, tokens["refresh_token"]).status_code == 400


# ---------------------------------------------------------------- revocation
def test_deactivation_revokes_everything(editor, claude_app):
    _tokens(editor, claude_app)
    issue_token(editor, claude_app)
    editor.is_active = False
    editor.save()
    assert not AccessToken.objects.filter(user=editor).exists()
    assert not RefreshToken.objects.filter(user=editor, revoked__isnull=True).exists()


def test_backend_security_signal_revokes():
    try:
        from apps.accounts.signals import user_deactivated  # noqa: F401
    except ImportError:
        pytest.skip("apps.accounts.signals lands with backend-security")
    from django.contrib.auth.models import User

    user = make_user("sig")
    app = Application.objects.create(name="x", client_type="confidential", authorization_grant_type="authorization-code",
                                     redirect_uris=CALLBACK)
    issue_token(user, app)
    user_deactivated.send(sender=User, user=user)
    assert not AccessToken.objects.filter(user=user).exists()


def test_cms_revoke_endpoint_own_access(editor, claude_app):
    _tokens(editor, claude_app)
    api = APIClient()
    api.force_authenticate(editor)
    listed = api.get("/api/v1/cms/claude-access/")
    assert listed.status_code == 200 and listed.json()["connected"] is True
    resp = api.post("/api/v1/cms/claude-access/revoke/", {}, format="json")
    assert resp.status_code == 200 and resp.json()["revoked"] >= 2
    assert not AccessToken.objects.filter(user=editor).exists()
    assert api.get("/api/v1/cms/claude-access/").json()["connected"] is False


def test_cms_revoke_other_user_needs_admin(editor, claude_app):
    victim = make_user("victim")
    issue_token(victim, claude_app)
    api = APIClient()
    api.force_authenticate(editor)
    resp = api.post("/api/v1/cms/claude-access/revoke/", {"user_id": victim.pk}, format="json")
    assert resp.status_code == 403 and resp.json()["code"] == "CMS_FORBIDDEN_ROLE"
    assert AccessToken.objects.filter(user=victim).exists()
    admin = make_user("boss", role="admin")
    api.force_authenticate(admin)
    assert api.post("/api/v1/cms/claude-access/revoke/", {"user_id": victim.pk}, format="json").status_code == 200
    assert not AccessToken.objects.filter(user=victim).exists()


def test_cms_revoke_requires_cms_role(claude_app):
    api = APIClient()
    api.force_authenticate(make_user("nope", role=None))
    assert api.post("/api/v1/cms/claude-access/revoke/", {}, format="json").status_code == 403
    assert APIClient().post("/api/v1/cms/claude-access/revoke/", {}, format="json").status_code in (401, 403)


# ---------------------------------------------------------------- DCR and the client command
def test_dcr_is_off_by_default():
    resp = Client().post("/oauth/register/", '{"redirect_uris": ["%s"]}' % CALLBACK, content_type="application/json")
    assert resp.status_code in (403, 404)
    assert not Application.objects.exists()


def test_dcr_when_enabled_only_registers_claude_callbacks(settings):
    from oauth2_provider.settings import oauth2_settings

    settings.MCP_OAUTH_DCR_ENABLED = True
    settings.OAUTH2_PROVIDER = {**settings.OAUTH2_PROVIDER, "DCR_ENABLED": True}
    oauth2_settings.reload()
    try:
        bad = Client().post("/oauth/register/", '{"redirect_uris": ["https://evil.example.com/cb"]}',
                            content_type="application/json")
        assert bad.status_code in (401, 403)
        good = Client().post("/oauth/register/", '{"redirect_uris": ["%s"], "token_endpoint_auth_method": "none", '
                             '"grant_types": ["authorization_code", "refresh_token"], "client_name": "Claude"}' % CALLBACK,
                             content_type="application/json")
        assert good.status_code == 201, good.content
        assert Application.objects.get(client_id=good.json()["client_id"]).redirect_uris == CALLBACK
    finally:
        settings.OAUTH2_PROVIDER = {**settings.OAUTH2_PROVIDER, "DCR_ENABLED": False}
        oauth2_settings.reload()


def test_create_claude_client_prints_secret_once():
    out = io.StringIO()
    call_command("create_claude_client", stdout=out)
    text = out.getvalue()
    secret = text.split("Client secret:")[1].split()[0]
    app = Application.objects.get(name="Claude")
    assert app.client_type == "confidential" and not app.skip_authorization
    assert app.redirect_uris.split() == ["https://claude.ai/api/mcp/auth_callback", "https://claude.com/api/mcp/auth_callback"]
    assert app.client_secret != secret  # stored hashed
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("create_claude_client", stdout=io.StringIO())
    out2 = io.StringIO()
    call_command("create_claude_client", "--rotate", stdout=out2)
    assert out2.getvalue().split("Client secret:")[1].split()[0] != secret
    assert Application.objects.filter(name="Claude").count() == 1


# ---------------------------------------------------------------- review fixes (19 Nov)
def test_dcr_client_cannot_put_its_redirect_uris_elsewhere(settings):
    """Regression: DOT's RFC 7592 PUT skipped the registration permission check."""
    import json

    from oauth2_provider.settings import oauth2_settings

    settings.MCP_OAUTH_DCR_ENABLED = True
    settings.OAUTH2_PROVIDER = {**settings.OAUTH2_PROVIDER, "DCR_ENABLED": True}
    oauth2_settings.reload()
    try:
        reg = Client().post("/oauth/register/", json.dumps({
            "redirect_uris": [CALLBACK], "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"], "client_name": "Claude"}),
            content_type="application/json").json()
        url = urlsplit(reg["registration_client_uri"]).path
        auth = {"HTTP_AUTHORIZATION": f"Bearer {reg['registration_access_token']}"}
        bad = Client().put(url, json.dumps({**reg, "redirect_uris": ["https://evil.example.com/cb"]}),
                           content_type="application/json", **auth)
        assert bad.status_code == 400 and bad.json()["error"] == "invalid_redirect_uri"
        assert Application.objects.get(client_id=reg["client_id"]).redirect_uris == CALLBACK
        assert Client().get(url, **auth).status_code == 200
    finally:
        settings.OAUTH2_PROVIDER = {**settings.OAUTH2_PROVIDER, "DCR_ENABLED": False}
        oauth2_settings.reload()


def test_consent_shows_client_name_and_redirect_host(editor, claude_app):
    _, challenge = pkce()
    html = signed_in(editor).get("/oauth/authorize/", authorize_params(claude_app, challenge)).content.decode()
    assert "Requested by <strong>Claude</strong>" in html and "<strong>claude.ai</strong>" in html


def test_revoke_user_id_is_normalised(editor, claude_app):
    issue_token(editor, claude_app)
    api = APIClient()
    api.force_authenticate(editor)
    assert api.post("/api/v1/cms/claude-access/revoke/", {"user_id": "abc"}, format="json").status_code == 400
    resp = api.post("/api/v1/cms/claude-access/revoke/", {"user_id": str(editor.pk)}, format="json")
    assert resp.status_code == 200 and resp.json()["user_id"] == editor.pk


def test_mcp_and_cms_hosts_are_allowed_hosts():
    import os
    import subprocess
    import sys

    env = {**os.environ, "MCP_PUBLIC_URL": "https://mcp.example.org", "CMS_PUBLIC_URL": "https://cms.example.org:8443",
           "ALLOWED_HOSTS": "internal.example.org", "DJANGO_SETTINGS_MODULE": "config.settings_test"}
    out = subprocess.run([sys.executable, "-c", "import django; django.setup(); from django.conf import settings; "
                          "print(','.join(settings.ALLOWED_HOSTS))"], env=env, capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))), check=True)
    hosts = out.stdout.strip().split(",")
    assert "mcp.example.org" in hosts and "cms.example.org" in hosts
