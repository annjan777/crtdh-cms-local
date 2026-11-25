"""Remove what the Claude connector left in the database.

The connector (apps `mcp_server`, `cms_oauth` and django-oauth-toolkit's `oauth2_provider`) has been taken out of
the code. Its tables, migration records, content types and permissions stay behind on databases that had it;
this drops them. On a fresh database there is nothing to drop and this does nothing.
"""
from django.db import migrations

APP_LABELS = ("mcp_server", "cms_oauth", "oauth2_provider")


def drop_connector_tables(apps, schema_editor):
    conn = schema_editor.connection
    tables = [t for t in conn.introspection.table_names() if t.startswith(tuple(f"{label}_" for label in APP_LABELS))]
    quote = schema_editor.quote_name
    with conn.cursor() as cur:
        for table in tables:
            if conn.vendor == "postgresql":
                cur.execute(f"DROP TABLE IF EXISTS {quote(table)} CASCADE")
            else:
                cur.execute(f"DROP TABLE IF EXISTS {quote(table)}")
        cur.execute("DELETE FROM django_migrations WHERE app IN (%s, %s, %s)", APP_LABELS)
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    stale = ContentType.objects.filter(app_label__in=APP_LABELS)
    Permission.objects.filter(content_type__in=stale).delete()
    stale.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0007_seed_page_heroes"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(drop_connector_tables, migrations.RunPython.noop)]
