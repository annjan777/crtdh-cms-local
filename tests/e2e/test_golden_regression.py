"""REGRESSION (CRITICAL) #1: the prerendered site shows the same content as the 19 Nov runtime SPA.

Golden: tests/e2e/golden/public_content.json, captured by scripts/capture-baseline-golden.sh from 834f59a
with the FULL seed. Run this with E2E_SEED=full and a site built from a snapshot of that DB.
Compares headings (text + order), item texts (order-insensitive set, must be a superset) and image count/alt.
Pixel parity is out of scope (visual baseline is separate).
"""
import json
from pathlib import Path

import pytest

from conftest import ROUTES

pytestmark = [pytest.mark.needs_integration]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "public_content.json").read_text())


@pytest.fixture(scope="module")
def current(site):
    import os
    if os.environ.get("E2E_SEED") != "full":
        pytest.skip("golden comparison needs E2E_SEED=full (same seed as the golden)")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.capture_golden import capture
    exe = os.environ.get("CHROME_BIN")
    try:
        return capture(site)
    except Exception:
        return capture(site, executable=exe)


@pytest.mark.parametrize("route", ROUTES)
def test_headings_unchanged(current, route):
    assert current[route]["headings"] == GOLDEN[route]["headings"]


@pytest.mark.parametrize("route", ROUTES)
def test_items_not_lost(current, route):
    lost = set(GOLDEN[route]["items"]) - set(current[route]["items"])
    assert not lost, f"{len(lost)} items missing, e.g. {sorted(lost)[:5]}"


@pytest.mark.parametrize("route", ROUTES)
def test_images_not_lost(current, route):
    g, c = GOLDEN[route]["images"], current[route]["images"]
    assert len(c) >= len(g), f"{len(g)} images before, {len(c)} now"
    missing_alt = {i["alt"] for i in g if i["alt"]} - {i["alt"] for i in c}
    assert not missing_alt, missing_alt
