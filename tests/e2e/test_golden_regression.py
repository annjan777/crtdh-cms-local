"""REGRESSION (CRITICAL) #1: the prerendered site shows the same content as the 19 Nov runtime SPA.

Golden: tests/e2e/golden/public_content.json, captured by scripts/capture-baseline-golden.sh from 834f59a
with the FULL seed. Run this with E2E_SEED=full and a site built from a snapshot of that DB.
Re-baselined 19 Nov (golden _meta): headings are the v3 redesign's; role badges ("RESEARCH MEMBER", …) are gone
by design. Checks: headings (text + order); every golden item's words are on the page (markup/order-insensitive,
badge words excluded); every published image in the build's snapshot appears on some page (the old SPA's image
*count* duplicated carousel slides, so it is not a loss measure).
Pixel parity is out of scope (visual baseline is separate).
"""
import re
import json
from pathlib import Path

import pytest

from conftest import ROUTES

pytestmark = [pytest.mark.needs_integration]
GOLDEN = {k: v for k, v in json.loads((Path(__file__).parent / "golden" / "public_content.json").read_text()).items()
          if not k.startswith("_")}
BADGES = re.compile(r"\b(research member|co-principal investigator|principal investigator|project manager|project staff|"
                    r"medical staff|research scholar)\b", re.I)


def _tokens(s):
    return set(re.findall(r"[a-z0-9@]+(?:[.'][a-z0-9]+)*", s.lower()))


def _page_tokens(site, route):
    import html
    import urllib.request
    h = urllib.request.urlopen(site + route, timeout=30).read().decode()
    return _tokens(html.unescape(re.sub(r"<[^>]+>", " ", h)) + " " + " ".join(re.findall(r'alt="([^"]*)"', h)))


@pytest.fixture(scope="module")
def current(site):
    import os
    if os.environ.get("E2E_SEED") != "full":
        pytest.skip("golden comparison needs E2E_SEED=full (same seed as the golden)")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import subprocess
    import tempfile
    # separate process: pytest-playwright already runs an event loop here, the sync API can't nest in it
    out = Path(tempfile.mkdtemp()) / "current.json"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "tools" / "capture_golden.py"),
                    "--site", site, "--out", str(out)], check=True, capture_output=True, text=True, timeout=600)
    return json.loads(out.read_text())


# The smoke and the publish specs write a marker into the first hero headline before this runs on preprod; that
# edit is the test's, not a content change, so it is put back to the seed headline before comparing.
TEST_EDIT = re.compile(r"^(Preprod smoke|Published by E2E|API publish) \d+")


def _normalise(headings):
    return [[tag, TEST_EDIT.sub("Common Research &", text)] for tag, text in headings]


@pytest.mark.parametrize("route", ROUTES)
def test_headings_unchanged(current, route):
    assert _normalise(current[route]["headings"]) == GOLDEN[route]["headings"]


@pytest.mark.parametrize("route", ROUTES)
def test_items_not_lost(site, route):
    page = _page_tokens(site, route)
    lost = []
    for item in GOLDEN[route]["items"]:
        need = {t for t in _tokens(BADGES.sub(" ", item)) if len(t) > 2}  # 2-char tile initials (3P, DE) are decoration
        if need - page:
            lost.append((item[:70], sorted(need - page)[:6]))
    assert not lost, f"{len(lost)} golden items not on the page: {lost[:6]}"


def test_published_images_all_rendered(site):
    """Every image a published row or singleton points at (snapshot media) appears on at least one page."""
    import glob
    import os
    import urllib.request
    snaps = sorted(glob.glob(os.path.join(os.environ.get("PREPROD_STATE", ".preprod"), "publish/builds/*/snapshot.json")),
                   key=os.path.getmtime)
    if not snaps:
        pytest.skip("needs the snapshot of the live build (preprod)")
    snap = json.loads(Path(snaps[-1]).read_text())
    seen = set()
    for r in ROUTES:
        seen |= set(re.findall(r"/_media/([0-9a-f]{16})", urllib.request.urlopen(site + r, timeout=30).read().decode()))
    refs = []
    for coll, rows in snap["collections"].items():
        for row in rows:
            refs += [(coll, row.get("id"), v) for v in row.values() if isinstance(v, str) and v.startswith("/_media/")]
    for name, row in snap["singletons"].items():
        refs += [(name, None, v) for v in row.values() if isinstance(v, str) and v.startswith("/_media/")]
    missing = [r for r in refs if not r[2].endswith(".pdf") and r[2].rsplit("/", 1)[1][:16] not in seen]
    assert not missing, missing[:8]
