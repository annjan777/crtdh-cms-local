"""The relay for hosts that refuse long query strings: /oauth/go/<base64url query> -> /oauth/authorize/?k=<key>."""

import base64
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from django.test import Client

from .conftest import make_user  # noqa: F401
from .test_oauth import CALLBACK, authorize_params, exchange, pkce, signed_in

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def b64(query: str) -> str:
    return base64.urlsafe_b64encode(query.encode()).rstrip(b"=").decode()


def relay(client, params) -> str:
    resp = client.get(f"/oauth/go/{b64(urlencode(params))}/")
    assert resp.status_code == 302, resp.content[:300]
    loc = resp["Location"]
    assert loc.startswith("/oauth/authorize/?k=") and len(urlsplit(loc).query) < 40
    return loc


def test_relay_then_consent_then_token(editor, claude_app):
    verifier, challenge = pkce()
    client = signed_in(editor)
    params = authorize_params(claude_app, challenge, resource="https://crtdh.example/mcp/index.php/mcp")
    loc = relay(client, params)
    page = client.get(loc)
    assert page.status_code == 200 and b'name="allow"' in page.content
    resp = client.post(loc, {**params, "allow": "Authorize"})
    assert resp.status_code == 302, resp.content[:300]
    back = urlsplit(resp["Location"])
    assert f"{back.scheme}://{back.netloc}{back.path}" == CALLBACK
    code = parse_qs(back.query)["code"][0]
    assert parse_qs(back.query)["state"] == ["st-123"]
    assert exchange(claude_app, code, verifier).status_code == 200


def test_signed_out_goes_to_login_with_a_short_next(claude_app):
    _, challenge = pkce()
    client = Client()
    loc = relay(client, authorize_params(claude_app, challenge))
    resp = client.get(loc)
    assert resp.status_code == 302
    nxt = parse_qs(urlsplit(resp["Location"]).query)["next"][0]
    assert nxt == loc  # the key, not the long request, travels through sign-in


@pytest.mark.parametrize("payload", ["", "!!!", b64("a" * 5000), b64("response_type=token&client_id=x")])
def test_bad_payloads_are_refused(claude_app, payload):
    resp = Client().get(f"/oauth/go/{payload or 'x'}/")
    assert resp.status_code in (400, 404)


def test_unknown_client_or_foreign_redirect_is_not_stored(claude_app):
    _, challenge = pkce()
    for extra in ({"client_id": "nope"}, {"redirect_uri": "https://evil.example/cb"}):
        q = urlencode(authorize_params(claude_app, challenge, **extra))
        assert Client().get(f"/oauth/go/{b64(q)}/").status_code == 400


def test_unknown_or_expired_key_shows_an_error(editor, claude_app):
    resp = signed_in(editor).get("/oauth/authorize/?k=doesnotexist")
    assert resp.status_code == 400 and b"Connect again" in resp.content
