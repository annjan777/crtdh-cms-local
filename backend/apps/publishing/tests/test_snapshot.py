"""Snapshot (contract §1), visibility and the build guard (contract §5)."""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.carousel.models import HeroSlide
from apps.publishing import guard, registry
from apps.publishing.guard import BuildGuardError
from apps.publishing.snapshot import build_snapshot, validate

from .conftest import image_file

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 11, 19, 9, 30, tzinfo=UTC)


def test_shape_and_schema(content, publisher):
    snap = build_snapshot(published_by=publisher, now=NOW)
    assert snap["schema_version"] == 1
    assert snap["published_at"] == "2026-11-19T09:30:00Z"
    assert snap["snapshot_id"].startswith("2026-11-19T09:30:00Z-") and len(snap["snapshot_id"]) == 27
    assert snap["published_by"] == "priya"
    assert set(snap["collections"]) == set(registry.COLLECTIONS)
    assert set(snap["singletons"]) == {"site-settings", "about-page", "home-page"}
    assert "contact-messages" not in snap["collections"]
    assert [p["id"] for p in snap["registry"]["pages"]][:2] == ["home", "about"]
    assert validate(snap) == []


def test_snapshot_id_is_content_addressed(content):
    a, b = build_snapshot(now=NOW), build_snapshot(now=NOW)
    assert a == b
    HeroSlide.objects.filter(pk=18).update(heading="Changed")
    assert build_snapshot(now=NOW)["snapshot_id"] != a["snapshot_id"]


@pytest.mark.regression_critical
def test_hidden_items_are_excluded(content):
    snap = build_snapshot(now=NOW)
    hero_ids = [r["id"] for r in snap["collections"]["hero-slides"]]
    assert 9001 not in hero_ids  # is_published=False in the sample
    assert all(r["is_published"] for rows in snap["collections"].values() for r in rows)


def test_hiding_a_parent_hides_children_and_nested_rows(content):
    from apps.innovations.models import Innovation, InnovationImage
    from apps.team.models import TeamCategory, TeamMember
    cat = TeamCategory.objects.filter(members__isnull=False).first()
    TeamCategory.objects.filter(pk=cat.pk).update(is_published=False)
    inn = InnovationImage.objects.first()
    InnovationImage.objects.filter(pk=inn.pk).update(is_published=False)
    snap = build_snapshot(now=NOW)
    member_ids = {r["id"] for r in snap["collections"]["team-members"]}
    assert not member_ids & set(TeamMember.objects.filter(category=cat).values_list("id", flat=True))
    assert inn.pk not in {r["id"] for r in snap["collections"]["innovation-images"]}
    parent = next(r for r in snap["collections"]["innovations"] if r["id"] == inn.innovation_id)
    assert inn.pk not in [i["id"] for i in parent["images"]]
    Innovation.objects.filter(pk=inn.innovation_id).update(is_published=False)
    snap = build_snapshot(now=NOW)
    assert not [r for r in snap["collections"]["innovation-images"] if r["innovation"] == inn.innovation_id]


def test_rows_sorted_by_order_then_id(content):
    from apps.facilities.models import Equipment
    Equipment.objects.update(order=5)
    rows = build_snapshot(now=NOW)["collections"]["equipment"]
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)
    first = Equipment.objects.order_by("-id").first()
    Equipment.objects.filter(pk=first.pk).update(order=0)
    assert build_snapshot(now=NOW)["collections"]["equipment"][0]["id"] == first.pk


def test_media_is_content_hashed_with_variants(content, media_root):
    from apps.facilities.models import Equipment
    image_file(media_root / "equipment" / "lathe.jpg", 2000, 1000)
    image_file(media_root / "equipment" / "copy.jpg", 2000, 1000)  # same bytes, other name -> same hash
    rows = list(Equipment.objects.order_by("id")[:2])
    Equipment.objects.filter(pk=rows[0].pk).update(image="equipment/lathe.jpg")
    Equipment.objects.filter(pk=rows[1].pk).update(image="equipment/copy.jpg")
    snap = build_snapshot(now=NOW)
    eq = {r["id"]: r for r in snap["collections"]["equipment"]}
    path = eq[rows[0].pk]["image"]
    assert path == eq[rows[1].pk]["image"]
    assert path.startswith("/_media/") and path.endswith(".jpg") and len(path) == len("/_media/") + 16 + 4
    entry = snap["media"][path]
    assert entry["width"] == 2000 and entry["height"] == 1000
    assert entry["source"] in ("equipment/lathe.jpg", "equipment/copy.jpg")
    assert [v["width"] for v in entry["variants"]["webp"]] == [480, 960, 1600]
    assert entry["variants"]["webp"][0]["url"] == path.replace(".jpg", "-480.webp")
    assert "avif" in entry["variants"]
    assert validate(snap) == []


def test_missing_media_file_becomes_null_with_warning(content, media_root):
    snap = build_snapshot(now=NOW)
    assert any("missing media file" in w for w in snap.get("warnings", []))
    assert not any(isinstance(v, str) and v.startswith("/_media/") and v not in snap["media"]
                   for rows in snap["collections"].values() for r in rows for v in r.values())


# ---- guard ------------------------------------------------------------------------------------------------------
def test_guard_passes_valid_snapshot(content):
    snap = build_snapshot(now=NOW)
    guard.check(snap, previous=snap)


def test_guard_missing_collection(content):
    snap = build_snapshot(now=NOW)
    del snap["collections"]["team-members"]
    with pytest.raises(BuildGuardError) as exc:
        guard.check(snap)
    assert exc.value.code == "CMS_BUILD_GUARD" and "team-members" in exc.value.body["message"]


def test_guard_schema_failure(content):
    snap = build_snapshot(now=NOW)
    snap["collections"]["hero-slides"][0]["is_published"] = False
    with pytest.raises(BuildGuardError) as exc:
        guard.check(snap)
    assert "schema" in exc.value.body["message"]


def test_guard_shrink_over_30_percent_needs_confirmation(content):
    prev = build_snapshot(now=NOW)
    cur = copy.deepcopy(prev)
    prev["collections"]["equipment"] = prev["collections"]["equipment"] * 10  # 30 rows before
    cur["collections"]["equipment"] = cur["collections"]["equipment"] * 6  # 18 after = -40%
    with pytest.raises(BuildGuardError) as exc:
        guard.check(cur, previous=prev)
    assert "equipment shrinks from 30 to 18 (-40%)" in exc.value.body["message"]
    guard.check(cur, previous=prev, confirm_shrink=True)
    cur["collections"]["equipment"] = prev["collections"]["equipment"][:21]  # -30% exactly is allowed
    guard.check(cur, previous=prev)


# ---- migration parity (TEST-PLAN critical) ---------------------------------------------------------------------
SEED = Path(__file__).resolve().parents[3] / "apps" / "core" / "fixtures" / "local_seed.json"
STUB = Path(__file__).with_name("fixtures") / "stub-snapshot.json"
SEED_MEDIA = Path(__file__).resolve().parents[3] / "seed_media"


@pytest.mark.regression_critical
@pytest.mark.slow
def test_first_snapshot_reproduces_todays_content(settings):
    """Load today's seed DB; build_snapshot() must contain the same rows and field values as the stub taken from
    the live API on 19 Nov (media compared by source file)."""
    from django.core.management import call_command
    call_command("loaddata", str(SEED), exclude=["auth.user"], verbosity=0)
    settings.MEDIA_ROOT = str(SEED_MEDIA)
    snap = build_snapshot(now=NOW)
    stub = json.loads(STUB.read_text())
    assert validate(snap) == []

    def norm(value, media):
        if isinstance(value, str) and value in media:
            return "media:" + media[value]["source"]
        if isinstance(value, str) and "/media/" in value:
            return "media:" + value.split("/media/", 1)[1]
        if isinstance(value, list):
            return [norm(v, media) for v in value]
        if isinstance(value, dict):
            return {k: norm(v, media) for k, v in value.items() if k not in ("version",)}
        return value

    def project(got, want):
        """Keep only what the stub has (new fields such as version/is_published are additions, not changes)."""
        if isinstance(want, dict) and isinstance(got, dict):
            return {k: project(got.get(k), v) for k, v in want.items()}
        if isinstance(want, list) and isinstance(got, list) and len(want) == len(got):
            return [project(g, w) for g, w in zip(got, want)]
        return got

    missing_sources = {w.split("missing media file ", 1)[1] for w in snap.get("warnings", [])}
    for name, stub_rows in stub["collections"].items():
        rows = snap["collections"][name]
        stub_sorted = sorted(stub_rows, key=lambda r: (r.get("order", 0), r["id"]))
        assert [r["id"] for r in rows] == [r["id"] for r in stub_sorted], name
        for got, want in zip(rows, stub_sorted):
            for key, want_value in want.items():
                got_value = norm(project(got[key], want_value), snap["media"])
                want_value = norm(want_value, {})
                if got_value is None and isinstance(want_value, str) and want_value.removeprefix("media:") in missing_sources:
                    continue  # file is missing on disk today too; reported in warnings
                assert got_value == want_value, (name, got["id"], key)
    for name, want in stub["singletons"].items():
        for key, value in want.items():
            assert norm(snap["singletons"][name][key], snap["media"]) == norm(value, {}), (name, key)
