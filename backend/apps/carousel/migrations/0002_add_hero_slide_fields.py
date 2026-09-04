# Generated manually to add missing HeroSlide fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("carousel", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="heroslide",
            name="description",
            field=models.TextField(
                blank=True,
                default="Building affordable healthcare technology for a billion people, at IIT Kharagpur.",
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="eyebrow",
            field=models.CharField(
                blank=True, default="DSIR · GOVERNMENT OF INDIA", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="heading",
            field=models.CharField(
                blank=True, default="Common Research &", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="heading_end",
            field=models.CharField(blank=True, default="Hub", max_length=255),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="highlight_heading",
            field=models.CharField(
                blank=True, default="Technology Development", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="is_published",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="primary_button_label",
            field=models.CharField(
                blank=True, default="Explore Innovations", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="primary_button_link",
            field=models.CharField(
                blank=True, default="/innovations", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="secondary_button_label",
            field=models.CharField(
                blank=True, default="About CRTDH", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="heroslide",
            name="secondary_button_link",
            field=models.CharField(
                blank=True, default="/about", max_length=255
            ),
        ),
    ]
