"""Data migration: ImageGridBlock.page / VideoBlock.page become registry page ids (apps/publishing/pages.py).

Existing values are normalised (case, spaces/underscores, known aliases). A value that still matches no page is
left as it is and reported, so no content is lost; the registry test fails until someone fixes it in the CMS.
"""
from django.db import migrations

PAGE_IDS = ["home", "about", "team", "innovations", "facilities", "services", "product", "enterprises",
            "social-impact", "covid-19", "media", "contact"]
ALIASES = {"covid19": "covid-19", "covid": "covid-19", "socialimpact": "social-impact", "products": "product",
           "enterprise": "enterprises", "facility": "facilities", "service": "services", "index": "home"}


def normalise(value):
    v = (value or "").strip().lower().strip("/").replace("_", "-").replace(" ", "-")
    if v in PAGE_IDS:
        return v
    return ALIASES.get(v.replace("-", ""), ALIASES.get(v, None))


def forwards(apps, schema_editor):
    for name in ("ImageGridBlock", "VideoBlock"):
        model = apps.get_model("common", name)
        for row in model.objects.all():
            new = normalise(row.page)
            if new and new != row.page:
                model.objects.filter(pk=row.pk).update(page=new)
            elif not new:
                print(f"\n  ! {name} {row.pk}: page {row.page!r} is not a registry page; fix it in the CMS")


class Migration(migrations.Migration):
    dependencies = [("common", "0003_document_is_published_document_version_and_more")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
