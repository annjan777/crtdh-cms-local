"""Sample content is inserted with explicit ids; on Postgres the id sequences must move past them, or the next
ORM create collides ("duplicate key value violates unique constraint ..._pkey"). Order-dependent before the fix."""
import pytest
from django.db import connection

from apps.core.models import NewsItem
from apps.team.models import TeamCategory, TeamMember

pytestmark = pytest.mark.django_db


def test_create_after_sample_content_does_not_reuse_an_id():
    if connection.vendor == "postgresql":  # make it deterministic: start the sequences from 1 like a fresh DB
        with connection.cursor() as cur:
            for model in (NewsItem, TeamMember):
                cur.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), 1, false)", [model._meta.db_table])
    from tests.support.content import load_sample_content
    load_sample_content()
    top = max(NewsItem.objects.values_list("id", flat=True))
    assert NewsItem.objects.create(text="new", order=99, is_published=True).pk > top
    cat = TeamCategory.objects.first()
    member_top = max(TeamMember.objects.values_list("id", flat=True))
    assert TeamMember.objects.create(category=cat, name="New Member").pk > member_top
