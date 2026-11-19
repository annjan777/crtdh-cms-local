import json
import re
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.publishing import registry
from apps.publishing.pages import PAGE_IDS

# The public site's routes (React Router 7 config, v3/frontend): index('...') is "/", route('x', ...) is "/x".
ROUTES_JS = Path(__file__).resolve().parents[4] / "frontend" / "app" / "routes.js"


def frontend_routes():
    text = ROUTES_JS.read_text()
    paths = {"/" + p for p in re.findall(r"\broute\(\s*'([^']+)'", text) if p != "*"}
    if re.search(r"\bindex\(", text):
        paths.add("/")
    return paths


@pytest.mark.contract
def test_every_frontend_route_has_a_registry_page_and_vice_versa():
    routes = frontend_routes()
    assert len(routes) == 12
    assert routes == {p["path"] for p in registry.REGISTRY["pages"]}


def test_registry_covers_every_content_resource():
    from config.urls import router
    routed = {prefix for prefix, *_ in router.registry} - {"contact-messages"}
    assert routed == set(registry.COLLECTIONS)
    assert set(registry.SINGLETONS) == {"site-settings", "about-page", "home-page"}
    used = {s["resource"] for _p, s in registry._views()}
    assert used == set(registry.RESOURCES), "every resource is editable from some section"


@pytest.mark.django_db
def test_every_field_exists_on_model_and_serializer():
    for _page, s in registry._views():
        res = registry.RESOURCES[s["resource"]]
        model_fields = {f.name for f in res.model_class._meta.get_fields()}
        ser_fields = set(res.serializer_class().fields)
        for fd in s["fields"]:
            assert fd["name"] in model_fields, (s["id"], fd["name"])
            assert fd["name"] in ser_fields, (s["id"], fd["name"])
            assert fd["type"] in registry.FIELD_TYPES
            for extra in ("alt_field", "position_field"):
                if fd.get(extra):
                    assert fd[extra] in model_fields and fd[extra] in ser_fields, (s["id"], fd[extra])
        for key in (s.get("filter") or {}):
            assert key.split("__")[0] in model_fields


def test_section_ids_unique_and_prefixed_by_page():
    ids = [s["id"] for _p, s in registry.all_sections()]
    assert len(ids) == len(set(ids))
    for page_id, s in registry.all_sections():
        assert s["id"].startswith(page_id + ".")


def test_item_ids_round_trip():
    assert registry.parse_item_id("home.hero.hero-slides:7") == ("home.hero", "hero-slides", 7)
    assert registry.parse_item_id("home.objective.home-page:1") == ("home.objective", "home-page", 1)
    for bad in ("home.hero.team-members:1", "nope.hero-slides:1", "home.hero.hero-slides", "home.hero.hero-slides:x"):
        with pytest.raises(ValueError):
            registry.parse_item_id(bad)


@pytest.mark.django_db
def test_page_scoped_sections_resolve_by_page(content):
    from apps.common.models import ImageGridBlock, ImageGridItem
    for block in ImageGridBlock.objects.all():
        assert registry.item_id("image-grid-blocks", block.pk, block).startswith(f"{block.page}.photo-sections.image-grid-blocks:")
    item = ImageGridItem.objects.select_related("block").first()
    assert registry.item_id("image-grid-items", item.pk, item).startswith(f"{item.block.page}.photo-sections.image-grid-items:")
    # dict rows (snapshot-only) resolve through the lookup
    row = {"id": 5, "block": 77}
    lookup = lambda res, pk: {"id": 77, "page": "covid-19"} if (res, pk) == ("image-grid-blocks", 77) else None
    assert registry.item_id("image-grid-items", 5, row, lookup) == "covid-19.photo-sections.image-grid-items:5"


@pytest.mark.django_db
def test_singleton_field_maps_to_its_section():
    assert registry.item_id("home-page", 1, field="women_text_1") == "home.rural.home-page:1"
    assert registry.item_id("site-settings", 1, field="facebook_url") == "site.social.site-settings:1"
    assert registry.item_id("site-settings", 1, field="address") == "contact.details.site-settings:1"


@pytest.mark.django_db
def test_export_registry_command_outputs_enriched_json():
    out = StringIO()
    call_command("export_registry", stdout=out)
    data = json.loads(out.getvalue())
    assert [p["id"] for p in data["pages"]] == PAGE_IDS
    hero = data["pages"][0]["sections"][0]
    image = hero["fields"][0]
    assert image == {**image, "name": "image", "type": "image", "min_width": 1600, "alt_field": "alt_text", "required": True}
    assert image["position_field"] == "image_position"
    heading = next(f for f in hero["fields"] if f["name"] == "heading")
    assert heading["max"] == 40  # registry limit, never above the model's max_length
    assert heading["label"] == "Headline" and heading["required"] is True


def test_block_and_video_page_are_registry_choices():
    from apps.common.models import ImageGridBlock, VideoBlock
    for model in (ImageGridBlock, VideoBlock):
        assert [c for c, _ in model._meta.get_field("page").choices] == PAGE_IDS


def test_page_normalising_migration():
    import importlib
    mig = importlib.import_module("apps.common.migrations.0004_normalize_block_pages")
    assert mig.normalise("Covid19") == "covid-19"
    assert mig.normalise("social_impact") == "social-impact"
    assert mig.normalise(" Facilities ") == "facilities"
    assert mig.normalise("Index") == "home"
    assert mig.normalise("something-else") is None
    assert mig.PAGE_IDS == PAGE_IDS
