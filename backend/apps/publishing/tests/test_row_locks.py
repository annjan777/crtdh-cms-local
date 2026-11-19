"""Row locks that Postgres accepts (QA wave 2 D1).

SQLite ignores FOR UPDATE, so a lock Postgres rejects ("FOR UPDATE cannot be applied to the nullable side of an
outer join") is green on SQLite. The static check below fails on either engine; the SQL check runs on Postgres.
"""
import ast
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.publishing.models import Publish

BACKEND = Path(__file__).resolve().parents[3]


def _chain_calls(node):
    """Method calls of one `a.b(...).c(...)` chain, outermost first: [(name, call), ...]."""
    out = []
    while True:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            out.append((node.func.attr, node))
            node = node.func.value
        elif isinstance(node, ast.Attribute):
            node = node.value
        else:
            return out


def test_no_select_for_update_joined_without_of():
    bad = []
    for path in BACKEND.rglob("*.py"):
        if "migrations" in path.parts or "tests" in path.parts or ".venv" in path.parts:
            continue
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            calls = dict(_chain_calls(node))
            lock = calls.get("select_for_update")
            if lock is not None and "select_related" in calls and not any(k.arg == "of" for k in lock.keywords):
                bad.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not bad, f"select_for_update() + select_related() without of=('self',): {sorted(set(bad))}"


@pytest.mark.django_db
def test_download_build_locks_only_the_publish_row(client, content, publish_env, publisher):
    from apps.publishing.tests.test_publish_agent import agent_call, built

    p = built(publisher)
    with CaptureQueriesContext(connection) as q:
        resp = agent_call(client, "GET", f"/api/v1/agent/builds/{p.id}.tar.gz")
    assert resp.status_code == 200
    b"".join(resp.streaming_content)
    p.refresh_from_db()
    assert p.fetched_at is not None
    if connection.features.has_select_for_update_of:  # Postgres: the lock names only the publish table
        table = Publish._meta.db_table
        locks = [x["sql"] for x in q.captured_queries if "FOR UPDATE" in x["sql"] and f'FROM "{table}"' in x["sql"]]
        assert locks and all(s.endswith(f'FOR UPDATE OF "{table}"') for s in locks), locks
