from django.db import models

from apps.common.versioning import VersionedModel


class Innovation(VersionedModel):
    class Status(models.TextChoices):
        NONE = "", "Not shown"
        RESEARCH = "research", "Research"
        PROTOTYPE = "prototype", "Prototype"
        FIELD = "field-evaluation", "Field evaluation"
        DEPLOYED = "deployed", "Deployed"
        COMMERCIALISED = "commercialised", "Commercialised"

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=60, blank=True, help_text="Groups technologies for the filter, e.g. Diagnostics.")
    status = models.CharField(max_length=20, choices=Status.choices, blank=True, default="")
    summary = models.CharField(max_length=220, blank=True, help_text="One or two lines for the portfolio list.")
    body = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        # Kept for code paths without the publishing app's pre_save hook; same shared allow-list.
        from apps.common.sanitize import clean_richtext

        self.body = clean_richtext(self.body)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class InnovationImage(VersionedModel):
    innovation = models.ForeignKey(Innovation, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="innovation_images/")
    image_alt = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers.")
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.caption or f"InnovationImage {self.pk}"
