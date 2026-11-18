from datetime import timedelta
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contact.models import ContactMessage
from tests.support.errors import assert_contract_error

pytestmark = [pytest.mark.django_db, pytest.mark.security]
URL = "/api/v1/contact/"
GOOD = {"name": "Asha Rao", "email": "Asha@Example.test", "phone": "+91 98300 00000",
        "message": "We would like to visit the lab next month.", "turnstile_token": "tok"}


@pytest.fixture(autouse=True)
def _fresh_cache(settings):
    from django.core.cache import cache
    cache.clear()
    settings.TURNSTILE_SECRET = "test-secret"


@pytest.fixture
def ok_turnstile():
    with mock.patch("apps.contact.turnstile.verify", return_value=True) as m:
        yield m


def post(client=None, ip="203.0.113.5", **data):
    client = client or APIClient(enforce_csrf_checks=True)
    return client.post(URL, dict(GOOD, **data), format="json", REMOTE_ADDR=ip)


def test_valid_message_stored_without_csrf_or_session(ok_turnstile):
    resp = post()
    assert resp.status_code == 201, resp.content
    msg = ContactMessage.objects.get()
    assert msg.email == "asha@example.test"
    assert "Set-Cookie" not in resp.headers or "session" not in resp.headers.get("Set-Cookie", "")
    assert "email" not in resp.json()  # nothing echoed back


def test_html_is_stored_escaped(ok_turnstile):
    post(name="<b>Bob</b>", message='<script>alert("x")</script> hello there')
    msg = ContactMessage.objects.get()
    assert "<script>" not in msg.message and "&lt;script&gt;" in msg.message
    assert msg.name == "&lt;b&gt;Bob&lt;/b&gt;"


def test_control_characters_dropped(ok_turnstile):
    post(message="hello\x07\x1b world, a real message")
    assert ContactMessage.objects.get().message == "hello world, a real message"
    assert post(message="nul \x00 byte message").status_code == 400


def test_turnstile_failure_is_400_and_nothing_stored():
    with mock.patch("apps.contact.turnstile.verify", return_value=False):
        resp = post()
    assert_contract_error(resp, "CMS_VALIDATION", status=400, field="turnstile_token")
    assert ContactMessage.objects.count() == 0


def test_turnstile_required_in_production_when_secret_missing(settings):
    settings.TURNSTILE_SECRET = ""
    settings.DEBUG = False
    from apps.contact import turnstile
    assert turnstile.verify("anything") is False


def test_turnstile_skipped_with_warning_in_debug(settings, caplog):
    settings.TURNSTILE_SECRET = ""
    settings.DEBUG = True
    from apps.contact import turnstile
    assert turnstile.verify(None) is True


def test_turnstile_posts_to_cloudflare_with_secret(settings):
    from apps.contact import turnstile
    fake = mock.MagicMock()
    fake.__enter__.return_value.read.return_value = b'{"success": true}'
    with mock.patch("urllib.request.urlopen", return_value=fake) as urlopen:
        assert turnstile.verify("tok", "198.51.100.1")
    req = urlopen.call_args[0][0]
    assert req.full_url == turnstile.VERIFY_URL and b"secret=test-secret" in req.data


def test_honeypot_pretends_success_and_stores_nothing(ok_turnstile):
    resp = post(website="http://spam.example")
    assert resp.status_code == 201
    assert ContactMessage.objects.count() == 0
    ok_turnstile.assert_not_called()


@pytest.mark.parametrize("field,value", [("name", "x" * 121), ("message", "y" * 4001), ("message", "short"),
                                         ("email", "not-an-email"), ("phone", "call me maybe")])
def test_length_and_format_limits(ok_turnstile, field, value):
    resp = post(**{field: value})
    assert_contract_error(resp, "CMS_VALIDATION", status=400, field=field)


def test_sixth_message_in_a_minute_is_429(ok_turnstile):
    for _ in range(5):
        assert post().status_code == 201
    resp = post()
    assert_contract_error(resp, "CMS_RATE_LIMITED", status=429)
    assert resp.headers["Retry-After"]
    assert post(ip="203.0.113.99").status_code == 201  # other IPs unaffected


def test_cf_connecting_ip_ignored_unless_behind_tunnel(ok_turnstile, settings):
    for i in range(5):
        APIClient().post(URL, GOOD, format="json", REMOTE_ADDR="203.0.113.5", HTTP_CF_CONNECTING_IP=f"198.51.100.{i}")
    resp = APIClient().post(URL, GOOD, format="json", REMOTE_ADDR="203.0.113.5", HTTP_CF_CONNECTING_IP="198.51.100.77")
    assert resp.status_code == 429  # spoofed header does not dodge the limit


def test_cf_connecting_ip_ignored_from_untrusted_peer_even_when_enabled(ok_turnstile, settings):
    """Review finding: a process reaching the container directly must not pick its own client IP."""
    settings.TRUST_CF_CONNECTING_IP = True
    settings.TRUSTED_PROXY_IPS = ["172.30.80.10", "172.30.80.11"]
    for i in range(5):
        APIClient().post(URL, GOOD, format="json", REMOTE_ADDR="172.30.81.7", HTTP_CF_CONNECTING_IP=f"198.51.100.{i}")
    resp = APIClient().post(URL, GOOD, format="json", REMOTE_ADDR="172.30.81.7", HTTP_CF_CONNECTING_IP="198.51.100.77")
    assert resp.status_code == 429


def test_cf_connecting_ip_used_behind_tunnel(ok_turnstile, settings):
    settings.TRUST_CF_CONNECTING_IP = True
    settings.TRUSTED_PROXY_IPS = ["172.18.0.5"]
    for i in range(6):
        resp = APIClient().post(URL, GOOD, format="json", REMOTE_ADDR="172.18.0.5",
                                HTTP_CF_CONNECTING_IP=f"198.51.100.{i}")
        assert resp.status_code == 201


def test_get_not_allowed():
    assert APIClient().get(URL).status_code == 405


def test_notification_email_has_no_personal_data(ok_turnstile, settings, mailoutbox):
    settings.CONTACT_NOTIFY_EMAIL = "enquiries@example.test"
    post()
    assert len(mailoutbox) == 1
    body = mailoutbox[0].body + mailoutbox[0].subject
    assert "Asha" not in body and "asha@example.test" not in body and "visit the lab" not in body


def test_purge_deletes_only_messages_past_retention(settings):
    settings.CONTACT_RETENTION_DAYS = 365
    old = ContactMessage.objects.create(name="a", email="a@example.test", message="old message here")
    new = ContactMessage.objects.create(name="b", email="b@example.test", message="new message here")
    ContactMessage.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=366))
    call_command("purge_contact_messages", "--dry-run")
    assert ContactMessage.objects.count() == 2
    call_command("purge_contact_messages")
    assert list(ContactMessage.objects.values_list("pk", flat=True)) == [new.pk]


@pytest.mark.parametrize("role,expected", [(None, 401), ("editor", 403), ("publisher", 200), ("admin", 200)])
def test_messages_readable_by_publisher_and_admin_only(api_as, role, expected):
    ContactMessage.objects.create(name="a", email="a@example.test", message="hello there friend")
    assert api_as(role).get("/api/v1/contact-messages/").status_code == expected
