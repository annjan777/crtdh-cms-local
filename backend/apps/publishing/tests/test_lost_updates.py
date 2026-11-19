"""Review finding MED/LOW: no silent lost update — every content write is `UPDATE ... WHERE version = <read>`."""
import pytest
from django.db import transaction
from django.db.models import F

from apps.carousel.models import HeroSlide
from apps.common.versioning import StaleWrite
from apps.publishing import changes
from apps.publishing import content as cms
from apps.publishing.audit import WriteContext
from apps.publishing.errors import CMSError

pytestmark = [pytest.mark.django_db, pytest.mark.regression_critical]


def concurrent_edit(pk, heading):
    HeroSlide.objects.filter(pk=pk).update(heading=heading, version=F("version") + 1)


def test_model_save_from_a_stale_read_raises(content):
    a, b = HeroSlide.objects.get(pk=18), HeroSlide.objects.get(pk=18)
    a.heading = "first"
    a.save()
    b.heading = "second"
    with pytest.raises(StaleWrite), transaction.atomic():
        b.save()
    row = HeroSlide.objects.get(pk=18)
    assert (row.heading, row.version) == ("first", 2) and b.version == 1


def test_update_item_race_becomes_409(content, editor, monkeypatch):
    real = cms._lock

    def racing_lock(model, pk):
        obj = real(model, pk)
        concurrent_edit(pk, "someone else")
        return obj

    monkeypatch.setattr(cms, "_lock", racing_lock)
    with pytest.raises(CMSError) as exc:
        cms.update_item("hero-slides", 18, {"heading": "mine"}, ctx=WriteContext(user=editor), expected_version=1)
    # (in this single-connection test the racing edit rolls back with ours; in production it is committed)
    assert exc.value.code == "CMS_STALE_VERSION"
    assert HeroSlide.objects.get(pk=18).heading != "mine"


def test_discard_race_becomes_409(baseline, editor, monkeypatch):
    ctx = WriteContext(user=editor)
    cms.update_item("hero-slides", 18, {"heading": "draft"}, ctx=ctx, expected_version=1)
    real = changes._apply_row

    def racing_apply(obj, *a, **kw):
        concurrent_edit(obj.pk, "edited meanwhile")
        return real(obj, *a, **kw)

    monkeypatch.setattr(changes, "_apply_row", racing_apply)
    published = {r["id"]: r for r in baseline.data["collections"]["hero-slides"]}[18]["heading"]
    with pytest.raises(CMSError) as exc:
        changes.discard_item("home.hero.hero-slides:18", ctx=ctx)
    assert exc.value.code == "CMS_STALE_VERSION"
    assert HeroSlide.objects.get(pk=18).heading != published  # the discard did not overwrite anything


def test_restore_race_becomes_409(baseline, editor, monkeypatch):
    ctx = WriteContext(user=editor)
    cms.update_item("hero-slides", 18, {"heading": "draft"}, ctx=ctx, expected_version=1)
    real = changes._apply_row

    def racing_apply(obj, *a, **kw):
        if obj.pk == 18 and isinstance(obj, HeroSlide):
            concurrent_edit(obj.pk, "edited meanwhile")
        return real(obj, *a, **kw)

    monkeypatch.setattr(changes, "_apply_row", racing_apply)
    published = {r["id"]: r for r in baseline.data["collections"]["hero-slides"]}[18]["heading"]
    with pytest.raises(CMSError) as exc:
        changes.restore_snapshot(baseline, ctx=ctx)
    assert exc.value.code == "CMS_STALE_VERSION"
    assert HeroSlide.objects.get(pk=18).heading != published
