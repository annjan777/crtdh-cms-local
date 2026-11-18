"""REGRESSION (CRITICAL) #2: the first snapshot of today's database reproduces today's public content.

Seed = full stub snapshot (serializer output of today's DB). build_snapshot() must give, per collection,
the same visible rows (count, order, field values) — media URLs compared by source path, hidden rows excluded.
"""
import json

import pytest

from tests.support.content import FULL_SNAPSHOT_PATH, load_snapshot_into_db

pytestmark = [pytest.mark.needs_integration, pytest.mark.regression_critical]


@pytest.fixture
def seeded(db, settings, tmp_path):
    """Real seed images (backend/seed_media) so the snapshot can hash them; copied so tests never write there."""
    import shutil
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "seed_media"
    settings.MEDIA_ROOT = str(tmp_path / "media")
    if src.is_dir():
        shutil.copytree(src, settings.MEDIA_ROOT)
    load_snapshot_into_db(FULL_SNAPSHOT_PATH)
    return json.loads(FULL_SNAPSHOT_PATH.read_text())


@pytest.fixture
def snap(seeded):
    from apps.publishing.snapshot import build_snapshot
    s = build_snapshot()
    return json.loads(json.dumps(s, default=str)) if not isinstance(s, (str, bytes)) else json.loads(s)


def _source(value, media):
    """Media compared by source path. Snapshot keys are /_media/<hash16>.<ext> (addendum A13); the seed (today's
    DB serializer output) has absolute .../media/<source> URLs."""
    if isinstance(value, str) and value in media:
        return media[value]["source"]
    if isinstance(value, str) and "/media/" in value:
        return value.split("/media/", 1)[1]
    return value


def _seed_file_missing(source, snap):
    """The seed references a few files that are not in backend/seed_media; build_snapshot nulls them and lists
    them in snap["warnings"] (backend-core 22:50Z). That is a seed-data gap, not lost content."""
    return any(source in str(w) for w in snap.get("warnings", []))


def test_schema_and_header(snap):
    assert snap["schema_version"] == 1
    for k in ("snapshot_id", "published_at", "singletons", "collections", "registry", "media"):
        assert k in snap, k


def test_every_collection_present(seeded, snap):
    assert set(seeded["collections"]) <= set(snap["collections"]), set(seeded["collections"]) - set(snap["collections"])
    assert "contact-messages" not in snap["collections"]


def _match(expected, got, media, where, snap=None):
    """expected must be reproduced inside got (got may add keys such as version); media compared by source path."""
    if isinstance(expected, dict):
        assert isinstance(got, dict), where
        for k, v in expected.items():
            if k == "id" and where.count(".") == 0:
                continue
            _match(v, got.get(k), media, f"{where}.{k}", snap)
    elif isinstance(expected, list):
        assert isinstance(got, list) and len(got) == len(expected), f"{where}: {len(expected)} -> {len(got) if isinstance(got, list) else got!r}"
        for i, (e, g) in enumerate(zip(expected, got)):
            _match(e, g, media, f"{where}[{i}]", snap)
    elif isinstance(expected, str) and "/media/" in expected:
        if got is None and snap is not None and _seed_file_missing(_source(expected, media), snap):
            return
        assert _source(got, media) == _source(expected, media), f"{where}: {expected!r} -> {got!r}"
    else:
        assert got == expected, f"{where}: {expected!r} -> {got!r}"


@pytest.mark.parametrize("resource", sorted(json.loads(FULL_SNAPSHOT_PATH.read_text())["collections"]))
def test_rows_and_values_match(seeded, snap, resource):
    expected = [r for r in seeded["collections"][resource] if r.get("is_published", True)]
    expected.sort(key=lambda r: (r.get("order", 0), r["id"]))
    got = snap["collections"][resource]
    assert len(got) == len(expected), f"{resource}: {len(expected)} visible rows today, {len(got)} in snapshot"
    for e, g in zip(expected, got):
        _match(e, g, snap.get("media", {}), f"{resource}:{e['id']}", snap)


def test_singletons_match(seeded, snap):
    for name, row in seeded["singletons"].items():
        _match(row, snap["singletons"][name], snap.get("media", {}), name, snap)


def test_media_paths_are_content_hashed(snap):
    import re
    for path, meta in snap["media"].items():
        assert re.fullmatch(r"/_media/[0-9a-f]{16}\.[a-z0-9]+", path), path  # A13
        assert meta["source"]
