"""Self-tests for the shared harness, so other lanes can trust it."""
import json

import pytest

from apps.accounts.roles import user_roles
from tests.support.content import SAMPLE_SNAPSHOT_PATH, resource_models
from tests.support.errors import assert_contract_error


@pytest.mark.parametrize("fixture,roles", [
    ("plain_user", []),
    ("editor", ["editor"]),
    ("publisher", ["editor", "publisher"]),
    ("cms_admin", ["editor", "publisher", "admin"]),
    ("superuser", ["editor", "publisher", "admin"]),
])
def test_role_fixtures(request, fixture, roles):
    assert user_roles(request.getfixturevalue(fixture)) == roles


def test_sample_content_loads_every_collection(sample_content):
    snap = json.loads(SAMPLE_SNAPSHOT_PATH.read_text())
    models = resource_models()
    for key, rows in snap["collections"].items():
        assert models[key].objects.count() == len(rows), key
    assert sample_content["team-members"] == len(snap["collections"]["team-members"])


def test_sample_content_has_edge_cases(sample_content):
    from apps.carousel.models import HeroSlide
    from apps.team.models import TeamMember
    assert HeroSlide.objects.filter(is_published=False).exists()
    assert TeamMember.objects.filter(name__regex=r"^.{80}$").exists()
    assert TeamMember.objects.filter(name__contains="অনন্যা").exists()


def test_frozen_clock(frozen):
    from django.utils import timezone
    assert timezone.now().isoformat().startswith("2026-11-19T09:30:00")


def test_api_as_sets_session_and_csrf(api_as, editor):
    client = api_as("editor")
    assert client.user == editor
    assert client.csrf_token


def test_contract_error_helper_accepts_valid_body():
    body = {"code": "CMS_STALE_VERSION", "message": "home.hero.hero-slides:7 changed (v7 vs v8, priya at 14:02).",
            "fix": "Reload the section and reapply your change.", "retryable": False, "side_effects": "none",
            "field": None, "current_version": 8, "request_id": "7f3a"}
    assert_contract_error(body, "CMS_STALE_VERSION", current_version=8)


@pytest.mark.parametrize("bad", [
    {"detail": "Not found."},
    {"code": "CMS_INTERNAL", "message": 'Traceback (most recent call last):\n File "x.py", line 3', "fix": "-",
     "retryable": True, "side_effects": "none", "request_id": "1"},
    {"code": "CMS_FETCH_BLOCKED", "message": "blocked https://x/a.jpg?X-Amz-Signature=abc", "fix": "-",
     "retryable": False, "side_effects": "none", "request_id": "1"},
])
def test_contract_error_helper_rejects_bad_bodies(bad):
    with pytest.raises(AssertionError):
        assert_contract_error(bad, bad.get("code", "CMS_NOT_FOUND"))
