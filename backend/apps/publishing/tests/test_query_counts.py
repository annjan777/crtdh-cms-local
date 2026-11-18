"""Review finding MED: snapshot and pending changes run a constant number of queries (no N+1)."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.publishing import changes, snapshot
from apps.publishing import content as cms
from apps.publishing.audit import WriteContext

pytestmark = pytest.mark.django_db


def count(fn):
    with CaptureQueriesContext(connection) as c:
        fn()
    return len(c.captured_queries)


def grow(editor, n):
    from apps.team.models import TeamCategory
    ctx = WriteContext(user=editor)
    cat = TeamCategory.objects.first()
    for i in range(n):
        cms.create_item("team-members", {"name": f"Member {i}", "category": cat.pk, "is_published": True}, ctx=ctx)
        cms.create_item("news-items", {"text": f"News {i}", "is_published": True}, ctx=ctx)


def test_snapshot_and_changes_queries_do_not_grow_with_rows(baseline, editor):
    grow(editor, 2)
    snap_small, changes_small = count(snapshot.build_snapshot), count(changes.pending_changes)
    grow(editor, 15)
    assert count(snapshot.build_snapshot) == snap_small <= 60
    assert count(changes.pending_changes) == changes_small <= 90
