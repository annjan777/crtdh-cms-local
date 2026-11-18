"""REGRESSION (CRITICAL) #2: the first snapshot of today's database reproduces today's public content.

Seed = full stub snapshot (serializer output of today's DB). build_snapshot() must give, per collection,
the same visible rows (count, order, field values) — media URLs compared by source path, hidden rows excluded.
"""
import json

import pytest

from tests.support.content import FULL_SNAPSHOT_PATH, load_snapshot_into_db

pytestmark = [pytest.mark.needs_integration, pytest.mark.regression_critical]
MEDIA_KEYS_HINT = ("image", "photo", "logo", "file", "pdf", "document", "video")


@pytest.fixture
def seeded(db):
    load_snapshot_into_db(FULL_SNAPSHOT_PATH)
    return json.loads(FULL_SNAPSHOT_PATH.read_text())


@pytest.fixture
def snap(seeded):
    from apps.publishing.snapshot import build_snapshot
    s = build_snapshot()
    return json.loads(json.dumps(s, default=str)) if not isinstance(s, (str, bytes)) else json.loads(s)


def _source(value, media):
    if isinstance(value, str) and value.startswith("/media/") and value in media:
        return media[value]["source"]
    if isinstance(value, str) and "/media/" in value:
        return value.split("/media/", 1)[1]
    return value


def test_schema_and_header(snap):
    assert snap["schema_version"] == 1
    for k in ("snapshot_id", "published_at", "singletons", "collections", "registry", "media"):
        assert k in snap, k


def test_every_collection_present(seeded, snap):
    assert set(seeded["collections"]) <= set(snap["collections"]), set(seeded["collections"]) - set(snap["collections"])
    assert "contact-messages" not in snap["collections"]


@pytest.mark.parametrize("resource", sorted(json.loads(FULL_SNAPSHOT_PATH.read_text())["collections"]))
def test_rows_and_values_match(seeded, snap, resource):
    media = snap.get("media", {})
    expected = [r for r in seeded["collections"][resource] if r.get("is_published", True)]
    expected.sort(key=lambda r: (r.get("order", 0), r["id"]))
    got = snap["collections"][resource]
    assert len(got) == len(expected), f"{resource}: {len(expected)} visible rows today, {len(got)} in snapshot"
    for e, g in zip(expected, got):
        for key, val in e.items():
            if key == "id":
                continue
            gv = g.get(key)
            if any(h in key for h in MEDIA_KEYS_HINT) and isinstance(val, str) and val:
                assert _source(gv, media) == _source(val, media), f"{resource}.{key}"
            else:
                assert gv == val, f"{resource}[{e['id']}].{key}: {val!r} -> {gv!r}"


def test_singletons_match(seeded, snap):
    media = snap.get("media", {})
    for name, row in seeded["singletons"].items():
        for key, val in row.items():
            if key == "id":
                continue
            assert _source(snap["singletons"][name].get(key), media) == _source(val, media), f"{name}.{key}"


def test_media_paths_are_content_hashed(snap):
    import re
    for path, meta in snap["media"].items():
        assert re.fullmatch(r"/media/[0-9a-f]{16}\.[a-z0-9]+", path), path
        assert meta["source"]
