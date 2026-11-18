"""Critical path: contact relay — valid stored; Turnstile failure 400; 6th/min/IP 429; HTML stored escaped.

Hook assumed (backend-security): apps.contact.turnstile.verify(token, remote_ip) -> bool. Monkeypatched here.
"""
import pytest

from tests.support.errors import assert_contract_error

pytestmark = [pytest.mark.needs_integration, pytest.mark.security]
URL = "/api/v1/contact/"


def payload(**kw):
    d = {"name": "Visitor", "email": "v@example.test", "subject": "Hello", "message": "Interested in a collaboration.",
         "turnstile_token": "XXXX.DUMMY.TOKEN.XXXX"}
    d.update(kw)
    return d


@pytest.fixture
def turnstile(monkeypatch):
    from apps.contact import turnstile as t
    state = {"ok": True}
    monkeypatch.setattr(t, "verify", lambda token, remote_ip=None, **k: state["ok"])
    return state


@pytest.fixture(autouse=True)
def _clear_throttle():
    from django.core.cache import cache
    cache.clear()


def test_valid_message_stored(api, turnstile):
    from apps.contact.models import ContactMessage
    r = api.post(URL, payload(), format="json", REMOTE_ADDR="198.51.100.7")
    assert r.status_code in (200, 201)
    assert ContactMessage.objects.count() == 1


def test_turnstile_failure_400(api, turnstile):
    turnstile["ok"] = False
    assert_contract_error(api.post(URL, payload(), format="json"), "CMS_VALIDATION")


def test_sixth_message_per_minute_429(api, turnstile, frozen):
    for _ in range(5):
        assert api.post(URL, payload(), format="json", REMOTE_ADDR="198.51.100.8").status_code in (200, 201)
    assert_contract_error(api.post(URL, payload(), format="json", REMOTE_ADDR="198.51.100.8"), "CMS_RATE_LIMITED")
    assert api.post(URL, payload(), format="json", REMOTE_ADDR="198.51.100.9").status_code in (200, 201)
    frozen.tick(61)
    assert api.post(URL, payload(), format="json", REMOTE_ADDR="198.51.100.8").status_code in (200, 201)


def test_html_stored_escaped(api, turnstile):
    from apps.contact.models import ContactMessage
    api.post(URL, payload(message="<script>alert(1)</script><b>hi</b>"), format="json")
    msg = ContactMessage.objects.get().message
    assert "<script" not in msg


def test_contact_is_the_only_anonymous_write_and_not_a_read(api, turnstile):
    assert api.get(URL).status_code in (401, 403, 405)
