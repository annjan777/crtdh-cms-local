from django.db import models
from apps.common.versioning import VersionedModel


class Service(VersionedModel):
    AUDIENCES = [
        ("", "Not set"),
        ("startups", "Startups and MSMEs"),
        ("researchers", "Researchers and academic groups"),
        ("industry", "Industry"),
        ("health", "Health workers and providers"),
    ]

    title = models.CharField(max_length=255)
    audience = models.CharField(max_length=20, choices=AUDIENCES, blank=True, default="",
                                help_text="Who this service is mainly for. Visitors can filter the list by it.")
    description = models.TextField(blank=True, help_text="One or two sentences: what the service is.")
    includes = models.TextField(blank=True, help_text="What is offered, one item per line.")
    how_to_access = models.TextField(blank=True, help_text="How a visitor gets this service, in one or two sentences.")
    cta_label = models.CharField(max_length=40, blank=True, help_text="Button text, for example 'Ask about testing'.")
    cta_link = models.CharField(max_length=255, blank=True, help_text="Where the button goes. Leave empty for the contact page.")
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title
