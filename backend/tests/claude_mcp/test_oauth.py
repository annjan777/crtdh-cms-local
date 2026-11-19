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


# ---------------------------------------------------------------- backend-security audit follow-ups
@pytest.mark.parametrize("signal_name", ["user_sessions_revoked", "user_deactivated"])
def test_account_signals_revoke_claude_tokens(claude_app, signal_name):
    """Password reset/change, MFA reset and 'sign out everywhere' fire user_sessions_revoked;
    a recovered account's Claude connector must lose access too."""
    import types

    from django.contrib.auth.models import User
    from django.dispatch import Signal

    from apps.oauth import signals as oauth_signals

    try:
        from apps.accounts import signals as real  # type: ignore
        module = real
    except ImportError:
        module = types.SimpleNamespace(user_deactivated=Signal(), user_sessions_revoked=Signal())
        assert set(oauth_signals.connect_account_signals(module)) == {"user_deactivated", "user_sessions_revoked"}
    try:
        user = make_user("recovered")
        issue_token(user, claude_app)
        bystander = make_user("bystander")
        issue_token(bystander, claude_app)
        getattr(module, signal_name).send(sender=User, user=user)
        assert not AccessToken.objects.filter(user=user).exists()
        assert AccessToken.objects.filter(user=bystander).exists()
    finally:
        if module is not getattr(oauth_signals, "_account_signals", None):
            oauth_signals.connect_account_signals(oauth_signals._account_signals or types.SimpleNamespace())


def test_consent_csp_allows_only_the_clients_redirect_origins(editor, claude_app, settings):
    settings.CONTENT_SECURITY_POLICY = ("default-src 'none'; style-src 'self'; frame-ancestors 'none'; "
                                        "form-action 'self'")
    _, challenge = pkce()
    client = signed_in(editor)
    page = client.get("/oauth/authorize/", authorize_params(claude_app, challenge))
    csp = page["Content-Security-Policy"]
    assert "form-action 'self' https://claude.ai https://claude.com" in csp
    assert csp.count("form-action") == 1 and "style-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp and "<style" not in page.content.decode()
    assert "/static/oauth/consent.css" in page.content.decode()
    # the POST response (302 to claude.ai) carries the same policy
    resp = client.post("/oauth/authorize/", {**authorize_params(claude_app, challenge), "allow": "Authorize"})
    assert resp.status_code == 302 and "https://claude.ai" in resp["Content-Security-Policy"]
    # another client's origins are not added
    other = Application.objects.create(name="Other", client_type="confidential",
                                       authorization_grant_type="authorization-code",
                                       redirect_uris="https://other.example.net/cb")
    resp = client.get("/oauth/authorize/", authorize_params(other, challenge, redirect_uri="https://other.example.net/cb"))
    assert "claude.ai" not in resp["Content-Security-Policy"]
    assert "https://other.example.net" in resp["Content-Security-Policy"]
    # an unknown client gets plain form-action 'self'
    resp = client.get("/oauth/authorize/", authorize_params(claude_app, challenge, client_id="nope"))
    assert resp["Content-Security-Policy"].endswith("form-action 'self'")


def test_consent_stylesheet_exists():
    from django.contrib.staticfiles import finders

    assert finders.find("oauth/consent.css")


def test_temporary_password_must_be_changed_before_connecting(editor, claude_app, monkeypatch):
    from apps.oauth import views as oauth_views

    monkeypatch.setattr(oauth_views, "must_change_password", lambda user: user.pk == editor.pk)
    _, challenge = pkce()
    resp = signed_in(editor).get("/oauth/authorize/", authorize_params(claude_app, challenge))
    assert resp.status_code == 302 and resp["Location"].startswith("/cms/login?next=/oauth/authorize/")


def test_must_change_password_reads_backend_security_flag(editor):
    from apps.oauth.mfa import must_change_password

    try:
        from apps.accounts.models import UserSecurity  # type: ignore
    except ImportError:
        assert must_change_password(editor) is False  # nothing to check before backend-security merges
        return
    UserSecurity.objects.update_or_create(user=editor, defaults={"must_change_password": True})
    assert must_change_password(editor) is True


# ---------------------------------------------------------------- QA wave 2 D5: consent POST from a real browser
def _csrf_consent_page(user, claude_app):
    import re

    client = Client(enforce_csrf_checks=True, HTTP_HOST="cms.example.org")
    client.force_login(user)
    session = client.session
    session[SESSION_FLAG] = user.pk
    session.save()
    _, challenge = pkce()
    params = authorize_params(claude_app, challenge)
    page = client.get("/oauth/authorize/", params, secure=True)
    assert page.status_code == 200
    html = page.content.decode()
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
    return client, page, html, {**params, "allow": "Authorize", "csrfmiddlewaretoken": token}


def test_consent_page_referrer_policy_lets_the_browser_send_its_origin(editor, claude_app):
    import re

    _, page, html, _ = _csrf_consent_page(editor, claude_app)
    metas = re.findall(r'<meta name="referrer" content="([^"]+)"', html)
    # no-referrer / never make Chrome send "Origin: null" on the form POST -> Django CSRF 403
    assert metas == ["same-origin"], metas
    assert "Origin: null" not in html  # template comment must not render
    assert page.get("Referrer-Policy", "same-origin") not in ("no-referrer", "never")


def test_consent_post_with_the_cms_origin_passes_csrf(editor, claude_app):
    client, _, _, form = _csrf_consent_page(editor, claude_app)
    resp = client.post("/oauth/authorize/", form, secure=True, HTTP_ORIGIN="https://cms.example.org")
    assert resp.status_code == 302, resp.content[:300]
    assert resp["Location"].startswith(CALLBACK) and "code=" in resp["Location"]


def test_consent_post_with_origin_null_is_what_csrf_refuses(editor, claude_app):
    # Documents why the referrer policy matters: this is what Chrome sent under no-referrer.
    client, _, _, form = _csrf_consent_page(editor, claude_app)
    assert client.post("/oauth/authorize/", form, secure=True, HTTP_ORIGIN="null").status_code == 403


def test_admin_lists_everyone_with_a_live_claude_connection(editor, claude_app):
    other = make_user("other_editor", first_name="Ola", last_name="Other")
    issue_token(other, claude_app)
    _tokens(editor, claude_app)
    api = APIClient()
    api.force_authenticate(editor)
    assert "users" not in api.get("/api/v1/cms/claude-access/").json()  # editors see only their own
    admin = make_user("boss2", role="admin")
    api.force_authenticate(admin)
    body = api.get("/api/v1/cms/claude-access/").json()
    assert body["connected"] is False and body["connections"] == []
    names = {u["username"]: u for u in body["users"]}
    assert set(names) == {editor.username}  # issue_token() alone makes no refresh token = no connection listed
    assert names[editor.username]["user_id"] == editor.pk and names[editor.username]["connections"][0]["client"]
    api.post("/api/v1/cms/claude-access/revoke/", {"user_id": editor.pk}, format="json")
    assert api.get("/api/v1/cms/claude-access/").json()["users"] == []
