"""Snapshot + build guard rules (contract §1, §5; TEST-PLAN edge cases)."""
import copy

import pytest

pytestmark = [pytest.mark.needs_integration, pytest.mark.contract]


@pytest.fixture
def snap(sample_content):
    from apps.publishing.snapshot import build_snapshot
    return build_snapshot()


def test_hidden_item_absent(snap):
    assert "HIDDEN SLIDE" not in str(snap)


def test_ordering_by_order_then_id(snap):
    for name, rows in snap["collections"].items():
        keys = [(r.get("order", 0), r.get("id", 0)) for r in rows]
        assert keys == sorted(keys), name


def test_validates_against_json_schema(snap):
    import json
    from pathlib import Path

    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[2] / "apps/publishing/snapshot.schema.json").read_text())
    jsonschema.validate(json.loads(json.dumps(snap, default=str)), schema)


def test_guard_rejects_missing_collection(snap):
    from apps.publishing import guard
    bad = copy.deepcopy(snap)
    del bad["collections"]["team-members"]
    with pytest.raises(Exception) as e:
        guard.check_snapshot(bad, previous=snap)
    assert "team-members" in str(e.value)


def test_guard_rejects_40pct_shrink_unless_confirmed(snap):
    from apps.publishing import guard
    prev = copy.deepcopy(snap)
    prev["collections"]["team-members"] = prev["collections"]["team-members"] * 2
    cur = copy.deepcopy(snap)
    cur["collections"]["team-members"] = prev["collections"]["team-members"][: int(len(prev["collections"]["team-members"]) * 0.6)]
    with pytest.raises(Exception):
        guard.check_snapshot(cur, previous=prev)
    guard.check_snapshot(cur, previous=prev, confirm_shrink=True)


def test_item_ids_are_stable_not_positional(sample_content):
    import json
    from apps.publishing.registry import export_registry
    reg = json.dumps(export_registry())
    assert "home.hero" in reg


def test_every_public_route_has_registry_page():
    from apps.publishing.registry import export_registry
    pages = {p["path"] for p in export_registry()["pages"]}
    assert pages == {"/", "/about", "/team", "/innovations", "/facilities", "/services", "/product", "/enterprises",
                     "/social-impact", "/covid-19", "/media", "/contact"}


def test_same_snapshot_twice_same_content(sample_content):
    from apps.publishing.snapshot import build_snapshot
    a, b = build_snapshot(), build_snapshot()
    for k in ("snapshot_id", "published_at"):
        a.pop(k, None), b.pop(k, None)
    assert a == b
