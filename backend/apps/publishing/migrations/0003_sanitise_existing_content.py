"""Clean rich text with the shared allow-list and blank unsafe links in rows stored before the write-path hook.
Changed rows get a version bump so an open editor tab sees a 409 instead of writing the old value back."""
from django.db import migrations
from django.db.models import F

# Field lists as of this migration (registry richtext/url fields + every URLField).
RICHTEXT = {
    ("core", "AboutPage"): ["intro", "mission_vision", "dsir_about", "iitkgp_about"],
    ("innovations", "Innovation"): ["body"],
}
URLS = {
    ("carousel", "HeroSlide"): ["primary_button_link", "secondary_button_link"],
    ("core", "NewsItem"): ["link_url"],
    ("core", "HomePage"): ["facility_card_1_link", "facility_card_2_link", "facility_card_3_link"],
    ("core", "NavItem"): ["url"],
    ("core", "SiteSettings"): ["map_embed_url", "facebook_url", "linkedin_url", "instagram_url", "twitter_url"],
    ("innovations", "Innovation"): ["video_url"],
    ("common", "VideoBlock"): ["youtube_url"],
    ("media_gallery", "MediaCoverageLink"): ["url"],
}


def forwards(apps, schema_editor):
    from apps.common.sanitize import clean_richtext, safe_url

    for key in set(RICHTEXT) | set(URLS):
        model = apps.get_model(*key)
        rich, urls = RICHTEXT.get(key, []), URLS.get(key, [])
        for row in model.objects.all().values("pk", *rich, *urls):
            changes = {}
            for name in rich:
                if row[name] and clean_richtext(row[name]) != row[name]:
                    changes[name] = clean_richtext(row[name])
            for name in urls:
                if row[name] and not safe_url(row[name]):
                    changes[name] = ""
            if changes:
                model.objects.filter(pk=row["pk"]).update(**changes, version=F("version") + 1)


class Migration(migrations.Migration):
    dependencies = [
        ("publishing", "0002_publish_fetched_at"),
        ("carousel", "0005_projectslide_image_alt"),
        ("common", "0005_imagegriditem_image_alt"),
        ("core", "0008_aboutpage_ecosystem_image_alt_and_more"),
        ("innovations", "0003_innovationimage_image_alt"),
        ("media_gallery", "0005_alter_mediaevent_slug"),
    ]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
