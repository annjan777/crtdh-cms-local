"""mcp_server schema after integration: photos live in apps.publishing's MediaAsset only."""
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db


def test_staged_image_table_is_gone_and_models_match_migrations():
    from io import StringIO

    from django.core.management import call_command

    assert "mcp_server_stagedimage" not in connection.introspection.table_names()
    out = StringIO()
    call_command("makemigrations", "mcp_server", "--check", "--dry-run", stdout=out)  # exits non-zero on drift
