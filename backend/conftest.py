"""Root pytest fixtures for the CRTDH backend (owned by the QA lane).

Other lanes: put lane-specific fixtures in apps/<app>/tests/conftest.py or tests/<area>/conftest.py.
Don't add a second root conftest. Helpers live in tests/support/.

Fixtures
  editor, publisher, cms_admin, superuser, plain_user  users with contract roles
  api                     anonymous DRF APIClient (CSRF *enforced*)
  api_as(role_or_user)    APIClient logged in by session, CSRF enforced, X-CSRFToken pre-set
  sample_content          trimmed stub snapshot loaded into the DB (+ returns counts)
  frozen                  freezegun at 2026-11-19 09:30 UTC; frozen.tick()/move_to()
  media_root              per-test MEDIA_ROOT in tmp_path
  mail_outbox             django.core.mail.outbox (cleared per test)
"""
import os

import pytest

INTEGRATION_ENV = "RUN_INTEGRATION"


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False,
                     help="run tests marked needs_integration (they depend on other lanes' code)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration") or os.environ.get(INTEGRATION_ENV) == "1":
        return
    skip = pytest.mark.skip(reason="needs_integration: run with --integration once the other lanes are merged")
    for item in items:
        if "needs_integration" in item.keywords:
            item.add_marker(skip)


# ---- users -----------------------------------------------------------------
@pytest.fixture
def plain_user(db):
    from tests.support.factories import make_user
    return make_user(None, username="norole")


@pytest.fixture
def editor(db):
    from tests.support.factories import make_user
    return make_user("editor", username="erin_editor", first_name="Erin", last_name="Editor")


@pytest.fixture
def publisher(db):
    from tests.support.factories import make_user
    return make_user("publisher", username="priya", first_name="Priya", last_name="Publisher")


@pytest.fixture
def cms_admin(db):
    from tests.support.factories import make_user
    return make_user("admin", username="ada_admin", first_name="Ada", last_name="Admin")


@pytest.fixture
def superuser(db):
    from tests.support.factories import make_user
    return make_user("superuser", username="root_su")


ROLE_FIXTURES = {"editor": "editor", "publisher": "publisher", "admin": "cms_admin",
                 "superuser": "superuser", "none": "plain_user"}


# ---- API clients -----------------------------------------------------------
def _csrf_ready(client):
    """Get a CSRF token the contract way: GET /api/v1/auth/csrf/ returns {"csrfToken": ...} in the body
    (the cookie is HttpOnly and named __Host-crtdh_csrf when DEBUG is off). Falls back to minting one
    with Django's helper and settings.CSRF_COOKIE_NAME. Sets X-CSRFToken on every request."""
    from django.conf import settings
    from django.middleware.csrf import _get_new_csrf_string
    token = None
    resp = client.get("/api/v1/auth/csrf/")
    if resp.status_code == 200:
        try:
            token = resp.json().get("csrfToken")
        except Exception:  # noqa: BLE001
            token = None
    if not token:
        token = _get_new_csrf_string()
        client.cookies[settings.CSRF_COOKIE_NAME] = token
    client.credentials(HTTP_X_CSRFTOKEN=token)
    client.csrf_token = token
    return client


def _mark_mfa_verified(client, user):
    """REQUIRED by backend-security: CMSSessionAuthentication ignores sessions without the MFA flag."""
    try:
        from apps.accounts import mfa  # type: ignore
    except Exception:
        return
    marker = getattr(mfa, "mark_session_verified", None)
    if marker:
        session = client.session
        marker(session, user)
        session.save()


@pytest.fixture
def api(db):
    from rest_framework.test import APIClient
    return _csrf_ready(APIClient(enforce_csrf_checks=True))


@pytest.fixture
def api_as(db, request):
    """api_as("editor") / api_as(user_obj) / api_as(None) -> APIClient with session + CSRF."""
    from rest_framework.test import APIClient

    def make(who):
        client = APIClient(enforce_csrf_checks=True)
        if who is None:
            return _csrf_ready(client)
        user = request.getfixturevalue(ROLE_FIXTURES[who]) if isinstance(who, str) else who
        client.force_login(user)
        _mark_mfa_verified(client, user)
        client.user = user
        return _csrf_ready(client)

    return make


# ---- content, time, media, mail -------------------------------------------
@pytest.fixture
def sample_content(db):
    from tests.support.content import load_sample_content
    return load_sample_content()


@pytest.fixture
def frozen():
    from freezegun import freeze_time
    with freeze_time("2026-11-19T09:30:00Z", tick=False) as ft:
        yield ft


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return tmp_path / "media"


@pytest.fixture
def mail_outbox(mailoutbox):
    return mailoutbox
